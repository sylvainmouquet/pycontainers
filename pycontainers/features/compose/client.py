import asyncio
import json
import time
from typing import TYPE_CHECKING, Any

from pycontainers.features.compose.detection import ComposeInvocation
from pycontainers.features.compose.service import ComposeService
from pycontainers.shared.errors import CommandError
from pycontainers.shared.logging import get_logger
from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    get_exit_code,
)

if TYPE_CHECKING:
    from pycontainers.shared.runtime.client import PyContainers
    from pycontainers.shared.runtime.detection import RuntimeBackend

logger = get_logger(__name__)

_COMPOSE_PROJECT_KWARGS = frozenset(
    {"file", "project_name", "project_directory", "env_file", "profile", "profiles"}
)


class _AsyncComposeCommandAccessor:
    """Async dynamic dispatch for compose subcommands."""

    def __init__(self, client: "ComposeClient") -> None:
        self._client = client

    def __getattr__(self, subcommand: str):
        async def command_wrapper(*args, **kwargs):
            return await self._client._dispatch_command(subcommand, *args, **kwargs)

        return command_wrapper


class ComposeClient:
    """Higher-level workflows for multi-container compose projects."""

    _NON_COMMAND_ATTRS = frozenset(
        {
            "aio",
            "parent",
            "backend",
            "_file",
            "_project_name",
            "_project_directory",
            "_env_file",
            "_profiles",
        }
    )

    def __init__(
        self,
        parent: "PyContainers",
        *,
        file: str | list[str] | tuple[str, ...] | None = None,
        project_name: str | None = None,
        project_directory: str | None = None,
        env_file: str | list[str] | tuple[str, ...] | None = None,
        profiles: str | list[str] | tuple[str, ...] | None = None,
        invocation: ComposeInvocation | None = None,
    ) -> None:
        self.parent = parent
        self._file = file
        self._project_name = project_name
        self._project_directory = project_directory
        self._env_file = env_file
        self._profiles = profiles
        self._invocation_override: ComposeInvocation | None = invocation

    @property
    def backend(self) -> "RuntimeBackend":
        return self.parent.backend

    @property
    def invocation(self) -> ComposeInvocation:
        from pycontainers.features.compose.detection import resolve_compose_invocation

        if self._invocation_override is not None:
            return self._invocation_override
        resolved = resolve_compose_invocation(self.backend)
        if resolved is None:
            raise RuntimeError(
                f"Compose is unavailable for backend {self.backend!r}; "
                f"install the compose plugin or {self.backend}-compose"
            )
        return resolved

    def _compose_command_prefix(self) -> list[str]:
        if self.invocation == "plugin":
            return ["compose"]
        return []

    def _project_option_parts(
        self,
        *,
        file: str | list[str] | tuple[str, ...] | None = None,
        project_name: str | None = None,
        project_directory: str | None = None,
        env_file: str | list[str] | tuple[str, ...] | None = None,
        profiles: str | list[str] | tuple[str, ...] | None = None,
    ) -> list[str]:
        parts: list[str] = []

        resolved_file = self._file if file is None else file
        if resolved_file is not None:
            files = (
                resolved_file
                if isinstance(resolved_file, (list, tuple))
                else [resolved_file]
            )
            for compose_file in files:
                parts.extend(["-f", str(compose_file)])

        resolved_project_name = (
            self._project_name if project_name is None else project_name
        )
        if resolved_project_name is not None:
            parts.extend(["-p", str(resolved_project_name)])

        resolved_project_directory = (
            self._project_directory if project_directory is None else project_directory
        )
        if resolved_project_directory is not None:
            parts.extend(["--project-directory", str(resolved_project_directory)])

        resolved_env_file = self._env_file if env_file is None else env_file
        if resolved_env_file is not None:
            env_files = (
                resolved_env_file
                if isinstance(resolved_env_file, (list, tuple))
                else [resolved_env_file]
            )
            for one_env_file in env_files:
                parts.extend(["--env-file", str(one_env_file)])

        resolved_profiles = self._profiles if profiles is None else profiles
        if resolved_profiles is not None:
            profile_list = (
                resolved_profiles
                if isinstance(resolved_profiles, (list, tuple))
                else [resolved_profiles]
            )
            for profile in profile_list:
                parts.extend(["--profile", str(profile)])

        return parts

    def _extract_project_kwargs(
        self, kwargs: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        project_kwargs: dict[str, Any] = {}
        command_kwargs: dict[str, Any] = {}

        for key, value in kwargs.items():
            if key in _COMPOSE_PROJECT_KWARGS:
                project_kwargs[key] = value
            else:
                command_kwargs[key] = value

        return project_kwargs, command_kwargs

    def _normalize_subcommand_kwargs(
        self, subcommand: str, kwargs: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        normalized = dict(kwargs)
        extra_parts: list[str] = []

        if subcommand == "down" and normalized.pop("volumes", None) is True:
            extra_parts.append("--volumes")

        if subcommand == "exec":
            tty = normalized.pop("tty", None)
            interactive = normalized.pop("interactive", None)
            if tty is not True and interactive is not True:
                extra_parts.append("-T")

        return normalized, extra_parts

    def _build_compose_command(
        self,
        subcommand: str,
        *args,
        project_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> list[str]:
        project_kwargs = project_kwargs or {}
        command_kwargs, extra_parts = self._normalize_subcommand_kwargs(
            subcommand, kwargs
        )
        command_parts = _build_command_line(
            subcommand,
            *args,
            skip_ps_defaults=subcommand == "ps",
            **command_kwargs,
        )

        if subcommand == "ps" and "--format" not in command_parts:
            insert_at = 1 if command_parts else 0
            command_parts[insert_at:insert_at] = ["--format", "json"]

        if subcommand == "exec" and extra_parts:
            insert_at = 1 if command_parts else 0
            command_parts[insert_at:insert_at] = extra_parts
            extra_parts = []

        return [
            *self._compose_command_prefix(),
            *self._project_option_parts(**project_kwargs),
            *command_parts,
            *extra_parts,
        ]

    def _parse_services(self, result_cleaned: str) -> list[ComposeService]:
        services: list[ComposeService] = []
        for row in result_cleaned.splitlines():
            if not row.strip():
                continue
            row_json = json.loads(row)
            service_name = row_json.get("Service") or row_json.get("Name")
            if not service_name:
                continue
            services.append(ComposeService(self, name=str(service_name), data=row_json))
        return services

    async def _dispatch_command(self, subcommand: str, *args, **kwargs) -> Any:
        start = time.perf_counter()
        project_kwargs, command_kwargs = self._extract_project_kwargs(kwargs)
        full_command_args = self._build_compose_command(
            subcommand,
            *args,
            project_kwargs=project_kwargs,
            **command_kwargs,
        )
        from pycontainers.features.compose.detection import resolve_compose_endpoint

        resolved_endpoint = resolve_compose_endpoint(self.backend, self.invocation)
        logger.info(
            "Dispatching compose command",
            subcommand=subcommand,
            backend=self.backend,
            invocation=self.invocation,
        )
        result, _ = await self.parent._execute_request(
            full_command_args=full_command_args,
            endpoint=resolved_endpoint,
        )
        exit_code = get_exit_code(result)
        result_cleaned = clean_result(result)
        duration_ms = round((time.perf_counter() - start) * 1000)

        if exit_code > 0:
            logger.error(
                "Compose command failed",
                subcommand=subcommand,
                backend=self.backend,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )
            raise CommandError(f"compose {subcommand}", exit_code, result_cleaned)

        logger.info(
            "Compose command completed",
            subcommand=subcommand,
            backend=self.backend,
            exit_code=exit_code,
            duration_ms=duration_ms,
        )

        if subcommand == "ps":
            return self._parse_services(result_cleaned)

        return result_cleaned.replace("\r\n\n", "")

    def service(self, name: str) -> ComposeService:
        """Return a service-level accessor for the given compose service name."""
        return ComposeService(self, name=name)

    @property
    def aio(self) -> _AsyncComposeCommandAccessor:
        """Async-first dynamic dispatch for compose subcommands."""
        return _AsyncComposeCommandAccessor(self)

    def __getattr__(self, subcommand: str):
        if subcommand in self._NON_COMMAND_ATTRS or subcommand.startswith("_"):
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {subcommand!r}"
            )

        def command_wrapper(*args, **kwargs):
            return asyncio.run(self._dispatch_command(subcommand, *args, **kwargs))

        return command_wrapper

    def __repr__(self) -> str:
        details: list[str] = []
        if self._file is not None:
            details.append(f"file={self._file!r}")
        if self._project_name is not None:
            details.append(f"project_name={self._project_name!r}")
        if self._project_directory is not None:
            details.append(f"project_directory={self._project_directory!r}")
        joined = ", ".join(details)
        if joined:
            return f"<ComposeClient ({self.backend}) {joined}>"
        return f"<ComposeClient ({self.backend})>"


class _ComposeAccessor:
    """Factory and default compose client exposed on runtime clients."""

    def __init__(self, parent: "PyContainers") -> None:
        self._parent = parent
        self._default_client = ComposeClient(parent)

    def __call__(
        self,
        *,
        file: str | list[str] | tuple[str, ...] | None = None,
        project_name: str | None = None,
        project_directory: str | None = None,
        env_file: str | list[str] | tuple[str, ...] | None = None,
        profiles: str | list[str] | tuple[str, ...] | None = None,
    ) -> ComposeClient:
        return ComposeClient(
            self._parent,
            file=file,
            project_name=project_name,
            project_directory=project_directory,
            env_file=env_file,
            profiles=profiles,
        )

    def __getattr__(self, subcommand: str):
        return getattr(self._default_client, subcommand)

    def service(self, name: str) -> ComposeService:
        return self._default_client.service(name)

    @property
    def aio(self) -> _AsyncComposeCommandAccessor:
        return self._default_client.aio

    def __repr__(self) -> str:
        return repr(self._default_client)
