import asyncio
import json
import weakref
from collections.abc import Mapping, Sequence
from typing import Any

import httpx
import nest_asyncio
from proxycraft import ProxyCraft
from proxycraft.config.models import Config

from pycontainers.features.compose.client import _ComposeAccessor
from pycontainers.shared.runtime.macos_commands import (
    adapt_command_line_for_macos,
    parse_macos_container_list,
    uses_macos_container_cli,
)
from pycontainers.shared.errors import CommandError, UnsupportedBackendError
from pycontainers.shared.logging import get_logger
from pycontainers.shared.runtime.config import CONFIGURATION
from pycontainers.shared.runtime.container import Container, ContainerEnv
from pycontainers.shared.runtime.detection import RuntimeBackend, detect_runtime
from pycontainers.shared.runtime.types import (
    PortPair,
    VolumeMapping,
    VolumeSequence,
    collect_ps_kwargs,
    collect_pull_kwargs,
    collect_run_kwargs,
)
from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    get_exit_code,
)

nest_asyncio.apply()

logger = get_logger(__name__)


class _AsyncCommandAccessor:
    """Async dynamic dispatch for container runtime CLI subcommands."""

    def __init__(self, client: "PyContainers") -> None:
        self._client = client

    async def run(
        self,
        image: str,
        *args: str,
        name: str | None = None,
        detach: bool = False,
        rm: bool = False,
        entrypoint: str | None = None,
        command: str | Sequence[str] | None = None,
        envs: Mapping[str, str] | None = None,
        volumes: VolumeMapping | VolumeSequence | None = None,
        expose: Sequence[int | str] | None = None,
        publish: Sequence[PortPair] | None = None,
        cap_add: Sequence[str] | None = None,
        **extra: Any,
    ) -> Container:
        kwargs = collect_run_kwargs(
            name=name,
            detach=detach,
            rm=rm,
            entrypoint=entrypoint,
            command=command,
            envs=envs,
            volumes=volumes,
            expose=expose,
            publish=publish,
            cap_add=cap_add,
            extra=extra,
        )
        return await self._client._dispatch_command("run", image, *args, **kwargs)

    async def ps(
        self,
        *args: str,
        all: bool = False,
        filter: Mapping[str, str] | None = None,
        filters: Mapping[str, str] | None = None,
        **extra: Any,
    ) -> list[Container]:
        kwargs = collect_ps_kwargs(
            all=all,
            filter=filter,
            filters=filters,
            extra=extra,
        )
        return await self._client._dispatch_command("ps", *args, **kwargs)

    async def pull(
        self,
        image: str | None = None,
        *,
        command: str | None = None,
        **extra: Any,
    ) -> str:
        kwargs = collect_pull_kwargs(command=command, extra=extra)
        if image is None and command is None:
            raise TypeError("pull() requires an image positional argument or command=")
        pull_target = image if image is not None else ""
        return await self._client._dispatch_command("pull", pull_target, **kwargs)

    def __getattr__(self, subcommand: str):
        if subcommand in _TYPED_COMMAND_ATTRS:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {subcommand!r}"
            )

        async def command_wrapper(*args, **kwargs):
            return await self._client._dispatch_command(subcommand, *args, **kwargs)

        return command_wrapper


_TYPED_COMMAND_ATTRS = frozenset({"run", "ps", "pull"})

_NON_COMMAND_ATTRS = frozenset(
    {
        "aio",
        "backend",
        "compose",
        "proxycraft",
        "transport",
        "loop",
        "startup_task",
        "_initialized",
        "_backend",
        "_endpoint",
        *_TYPED_COMMAND_ATTRS,
    }
)


class PyContainers:
    def __init__(
        self,
        backend: RuntimeBackend | None = None,
        debug: bool = False,
    ):
        if backend is None:
            backend = detect_runtime()
        if backend not in ("docker", "podman"):
            raise UnsupportedBackendError(backend)

        self._backend: RuntimeBackend = backend
        self._endpoint = f"/{backend}"
        self.proxycraft: ProxyCraft = ProxyCraft(config=Config(**CONFIGURATION))

        self._initialized = False
        try:
            self.loop = asyncio.get_running_loop()
            self.startup_task = asyncio.create_task(self.proxycraft.startup_event())

            logger.debug("We're in an asyncio context")
        except RuntimeError:
            logger.debug("We're NOT in an asyncio context")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.proxycraft.startup_event())

        self.transport = httpx.ASGITransport(app=self.proxycraft.app)
        weakref.finalize(self, self._cleanup_sync, self.proxycraft, self.loop)

    @property
    def backend(self) -> RuntimeBackend:
        return self._backend

    async def _session_client(self, app, method, payload, stream):
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport, base_url="http://pycontainers"
        ) as client:
            if stream:
                async with client.stream(
                    url=self._endpoint,
                    method=method,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    yield response
            else:
                response = await client.request(
                    url=self._endpoint,
                    method=method,
                    json=payload,
                )
                response.raise_for_status()
                yield response

    async def _load_env_from_inspect(self, container_id: str) -> ContainerEnv | None:
        inspect_args = _build_command_line("inspect", container_id)
        inspect_result, _ = await self._execute_request(full_command_args=inspect_args)
        inspect_exit_code = get_exit_code(inspect_result)
        if inspect_exit_code != 0:
            return None

        inspect_result_cleaned = clean_result(inspect_result).strip()
        if not inspect_result_cleaned:
            return None

        parsed = json.loads(inspect_result_cleaned)
        inspect_data: dict[str, Any] | None = None
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            inspect_data = parsed[0]
        elif isinstance(parsed, dict):
            inspect_data = parsed

        if not inspect_data:
            return None

        config = inspect_data.get("Config")
        if not isinstance(config, dict):
            return None

        env = config.get("Env")
        if isinstance(env, list):
            return Container._parse_env_variables([str(item) for item in env])
        return None

    async def _load_env_from_exec(self, container_id: str) -> ContainerEnv | None:
        exec_args = _build_command_line("exec", container_id, "env")
        exec_result, _ = await self._execute_request(full_command_args=exec_args)
        exec_exit_code = get_exit_code(exec_result)
        if exec_exit_code != 0:
            return None

        exec_result_cleaned = clean_result(exec_result).strip()
        if not exec_result_cleaned:
            return None

        values = [line for line in exec_result_cleaned.splitlines() if line.strip()]
        return Container._parse_env_variables(values)

    async def _build_run_container(
        self, container_id: str, runtime_envs: Any
    ) -> Container:
        container = Container(parent=self, ID=container_id)
        env: ContainerEnv | None = None

        try:
            env = await self._load_env_from_inspect(container.ID)
        except Exception:
            env = None

        if env is None:
            try:
                env = await self._load_env_from_exec(container.ID)
            except Exception:
                env = None

        if env is None and isinstance(runtime_envs, dict):
            env = ContainerEnv(
                {str(key): str(value) for key, value in runtime_envs.items()}
            )

        if env is not None:
            container.config = Container(
                parent=self,
                data={"env": env},
            )

        return container

    def _prepare_command_args(self, subcommand: str, *args, **kwargs) -> list[str]:
        full_command_args = _build_command_line(subcommand, *args, **kwargs)
        if uses_macos_container_cli(self._backend):
            return adapt_command_line_for_macos(full_command_args)
        return full_command_args

    async def _dispatch_command(self, subcommand: str, *args, **kwargs) -> Any:
        full_command_args = self._prepare_command_args(subcommand, *args, **kwargs)
        result, _ = await self._execute_request(full_command_args=full_command_args)
        exit_code = get_exit_code(result)
        result_cleaned = clean_result(result)

        if exit_code > 0:
            raise CommandError(subcommand, exit_code, clean_result(result))

        if subcommand == "run":
            container_id = result_cleaned.replace("\r\n\n", "")
            return await self._build_run_container(container_id, kwargs.get("envs"))

        if subcommand == "ps":
            rows: list[dict[str, Any]]
            if uses_macos_container_cli(self._backend):
                rows = parse_macos_container_list(result_cleaned)
            else:
                rows = [
                    json.loads(row) for row in result_cleaned.split("\n") if row != ""
                ]
            return [Container(parent=self, **row_json) for row_json in rows]

        return result_cleaned.replace("\r\n\n", "")

    def run(
        self,
        image: str,
        *args: str,
        name: str | None = None,
        detach: bool = False,
        rm: bool = False,
        entrypoint: str | None = None,
        command: str | Sequence[str] | None = None,
        envs: Mapping[str, str] | None = None,
        volumes: VolumeMapping | VolumeSequence | None = None,
        expose: Sequence[int | str] | None = None,
        publish: Sequence[PortPair] | None = None,
        cap_add: Sequence[str] | None = None,
        **extra: Any,
    ) -> Container:
        kwargs = collect_run_kwargs(
            name=name,
            detach=detach,
            rm=rm,
            entrypoint=entrypoint,
            command=command,
            envs=envs,
            volumes=volumes,
            expose=expose,
            publish=publish,
            cap_add=cap_add,
            extra=extra,
        )
        return asyncio.run(self._dispatch_command("run", image, *args, **kwargs))

    def ps(
        self,
        *args: str,
        all: bool = False,
        filter: Mapping[str, str] | None = None,
        filters: Mapping[str, str] | None = None,
        **extra: Any,
    ) -> list[Container]:
        kwargs = collect_ps_kwargs(
            all=all,
            filter=filter,
            filters=filters,
            extra=extra,
        )
        return asyncio.run(self._dispatch_command("ps", *args, **kwargs))

    def pull(
        self,
        image: str | None = None,
        *,
        command: str | None = None,
        **extra: Any,
    ) -> str:
        kwargs = collect_pull_kwargs(command=command, extra=extra)
        if image is None and command is None:
            raise TypeError("pull() requires an image positional argument or command=")
        pull_target = image if image is not None else ""
        return asyncio.run(self._dispatch_command("pull", pull_target, **kwargs))

    @property
    def aio(self) -> _AsyncCommandAccessor:
        """Async-first dynamic dispatch for container runtime CLI subcommands."""
        return _AsyncCommandAccessor(self)

    @property
    def compose(self) -> _ComposeAccessor:
        """Compose project lifecycle helpers and service-level accessors."""
        return _ComposeAccessor(self)

    def __getattr__(self, subcommand: str):
        """Handle any method call dynamically."""
        if subcommand in _NON_COMMAND_ATTRS or subcommand.startswith("_"):
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {subcommand!r}"
            )

        def command_wrapper(*args, **kwargs):
            return asyncio.run(self._dispatch_command(subcommand, *args, **kwargs))

        return command_wrapper

    async def _execute_request(self, full_command_args: list[str]) -> Any:
        logger.debug(f"command args : {full_command_args}")
        async for response in self._session_client(
            app=self.proxycraft.app,
            method="GET",
            stream=False,
            payload={"args": full_command_args},
        ):
            return response.text, response.status_code
        return None

    async def close(self):
        """Async cleanup method"""
        await self.proxycraft.shutdown_event()

    def __del__(self):
        """Synchronous cleanup - calls async close() properly"""
        try:
            current_loop = asyncio.get_running_loop()
            current_loop.create_task(self.close())
        except RuntimeError:
            loop = getattr(self, "loop", None)
            if isinstance(loop, asyncio.AbstractEventLoop) and not loop.is_closed():
                asyncio.set_event_loop(self.loop)
                try:
                    self.loop.run_until_complete(self.close())
                finally:
                    self.loop.close()
            else:
                try:
                    asyncio.run(self.close())
                except Exception:
                    ...

    @staticmethod
    def _cleanup_sync(proxy: Any, loop: asyncio.AbstractEventLoop):
        """Static cleanup method for weakref.finalize"""
        if loop and not loop.is_closed():
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(proxy.shutdown_event())
                loop.close()
            except Exception as e:
                print(f"Warning: Cleanup failed: {e}")
