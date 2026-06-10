import asyncio
from typing import Any

from pycontainers.shared.errors import CommandError
from pycontainers.shared.logging import get_logger
from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    get_exit_code,
)

logger = get_logger(__name__)


class _AsyncContainerCommandAccessor:
    """Async dynamic dispatch for container-scoped runtime CLI subcommands."""

    def __init__(self, container: "Container") -> None:
        self._container = container

    async def execute(self, *args, **kwargs) -> str:
        return await self._container._dispatch_command("execute", *args, **kwargs)

    def __getattr__(self, subcommand: str):
        async def command_wrapper(*args, **kwargs):
            return await self._container._dispatch_command(subcommand, *args, **kwargs)

        return command_wrapper


class ContainerEnv(dict[str, str]):
    """Dict-like env mapping that also iterates as KEY=VALUE strings."""

    def __iter__(self):
        for key, value in self.items():
            yield f"{key}={value}"


class Container:
    _NON_COMMAND_ATTRS = frozenset({"aio", "parent", "_data"})
    parent: Any
    config: "Container | None" = None
    _data: dict[str, Any] | None = None

    def __init__(self, parent, data: dict[str, Any] | None = None, **kwargs):
        """
        Initialize container with data from dict or kwargs

        Args:
            data: Dictionary to convert to attributes
            **kwargs: Additional keyword arguments to set as attributes
        """
        self.parent = parent

        if data is not None:
            for key, value in data.items():
                self._set_attribute(key, value)

        for key, value in kwargs.items():
            self._set_attribute(key, value)

        self._data = data

    def _set_attribute(self, key: str, value: Any) -> None:
        normalized_key = "config" if key.lower() == "config" else key
        if normalized_key == "config" and isinstance(value, dict):
            value = self._build_config(value)
        setattr(self, normalized_key, value)

    @staticmethod
    def _parse_env_variables(values: list[str]) -> ContainerEnv:
        env = ContainerEnv()
        for item in values:
            if "=" in item:
                name, value = item.split("=", 1)
                env[name] = value
            else:
                env[item] = ""
        return env

    def _build_config(self, config: dict[str, Any]) -> "Container":
        normalized_config = dict(config)
        if "env" not in normalized_config and "Env" in normalized_config:
            normalized_config["env"] = normalized_config["Env"]
        env = normalized_config.get("env")
        if isinstance(env, list):
            normalized_config["env"] = self._parse_env_variables(env)
        elif isinstance(env, dict) and not isinstance(env, ContainerEnv):
            normalized_config["env"] = ContainerEnv(
                {str(key): str(value) for key, value in env.items()}
            )
        return Container(parent=self.parent, data=normalized_config)

    def __str__(self) -> str:
        """User-friendly string representation"""
        return self.__repr__()

    def _resolve_command_args(
        self, subcommand: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[str, tuple[Any, ...]]:
        runtime_subcommand = "exec" if subcommand == "execute" else subcommand
        command_args = args
        if runtime_subcommand == "exec" and len(args) == 1 and not kwargs:
            if isinstance(args[0], str):
                command_args = ("sh", "-c", args[0])
            elif isinstance(args[0], (list, tuple)):
                command_args = tuple(str(part) for part in args[0])
        return runtime_subcommand, command_args

    async def _dispatch_command(self, subcommand: str, *args, **kwargs) -> str:
        runtime_subcommand, command_args = self._resolve_command_args(
            subcommand, args, kwargs
        )
        full_command_args = _build_command_line(
            runtime_subcommand,
            self.ID,
            *command_args,
            **kwargs,
        )

        result, _ = await self.parent._execute_request(
            full_command_args=full_command_args
        )
        exit_code = get_exit_code(result)
        result_cleaned = clean_result(result)

        if exit_code > 0:
            raise CommandError(runtime_subcommand, exit_code, result_cleaned)

        return result_cleaned

    @property
    def aio(self) -> _AsyncContainerCommandAccessor:
        """Async-first dispatch for container-scoped commands such as execute."""
        return _AsyncContainerCommandAccessor(self)

    def __getattr__(self, subcommand: str, *args, **kwargs) -> Any:
        if self._data and subcommand in self._data:
            return self._data[subcommand]

        if subcommand in self._NON_COMMAND_ATTRS or subcommand.startswith("_"):
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {subcommand!r}"
            )

        def command_wrapper(*args, **kwargs):
            return asyncio.run(self._dispatch_command(subcommand, *args, **kwargs))

        return command_wrapper
