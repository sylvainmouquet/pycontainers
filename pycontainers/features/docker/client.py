import asyncio
import json
import weakref
from typing import Any

import httpx
import nest_asyncio
from proxycraft import ProxyCraft
from proxycraft.config.models import Config

from pycontainers.features.docker.config import CONFIGURATION
from pycontainers.features.docker.container import Container, ContainerEnv
from pycontainers.shared.logging import get_logger
from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    get_exit_code,
)

nest_asyncio.apply()

logger = get_logger(__name__)


class PyContainers:
    async def _session_client(self, app, method, payload, stream):
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport, base_url="http://pycontainers"
        ) as client:
            if stream:
                async with client.stream(
                    url="/docker",
                    method=method,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    yield response
            else:
                response = await client.request(
                    url="/docker",
                    method=method,
                    json=payload,
                )
                response.raise_for_status()
                yield response

    def _load_env_from_inspect(self, container_id: str) -> ContainerEnv | None:
        inspect_args = _build_command_line("inspect", container_id)
        inspect_result, _ = asyncio.run(
            self._execute_request(full_command_args=inspect_args)
        )
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

    def _load_env_from_exec(self, container_id: str) -> ContainerEnv | None:
        exec_args = _build_command_line("exec", container_id, "env")
        exec_result, _ = asyncio.run(self._execute_request(full_command_args=exec_args))
        exec_exit_code = get_exit_code(exec_result)
        if exec_exit_code != 0:
            return None

        exec_result_cleaned = clean_result(exec_result).strip()
        if not exec_result_cleaned:
            return None

        values = [line for line in exec_result_cleaned.splitlines() if line.strip()]
        return Container._parse_env_variables(values)

    def __getattr__(self, command: str):
        """Handle any method call dynamically."""

        def command_wrapper(*args, **kwargs):
            full_command_args = _build_command_line(command, *args, **kwargs)
            result, command_status = asyncio.run(
                self._execute_request(full_command_args=full_command_args)
            )
            exit_code = get_exit_code(result)
            result_cleaned = clean_result(result)

            if exit_code > 0:
                raise ValueError(result)

            if command == "run":
                container = Container(
                    parent=self, ID=result_cleaned.replace("\r\n\n", "")
                )

                runtime_envs = kwargs.get("envs")
                env: ContainerEnv | None = None

                try:
                    env = self._load_env_from_inspect(container.ID)
                except Exception:
                    env = None

                if env is None:
                    try:
                        env = self._load_env_from_exec(container.ID)
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

            if command == "ps":
                containers = []
                for row in result_cleaned.split("\n"):
                    if row != "":
                        row_json = json.loads(row)
                        containers.append(Container(parent=self, **row_json))
                return containers
            return result_cleaned.replace("\r\n\n", "")

        return command_wrapper

    async def _execute_request(self, full_command_args: str) -> Any:
        logger.debug(f"command args : {full_command_args}")
        async for response in self._session_client(
            app=self.proxycraft.app,
            method="GET",
            stream=False,
            payload={"args": full_command_args},
        ):
            return response.text, response.status_code
        return None

    def __init__(
        self,
        debug: bool = False,
    ):
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

    async def close(self):
        """Async cleanup method"""
        await self.proxycraft.shutdown_event()

    def __del__(self):
        """Synchronous cleanup - calls async close() properly"""
        try:
            current_loop = asyncio.get_running_loop()
            current_loop.create_task(self.close())
        except RuntimeError:
            if hasattr(self, "loop") and self.loop and not self.loop.is_closed():
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
