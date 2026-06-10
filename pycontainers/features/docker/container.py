import asyncio
from typing import Any

from pycontainers.shared.logging import get_logger
from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    get_exit_code,
)

logger = get_logger(__name__)


class ContainerEnv(dict[str, str]):
    """Dict-like env mapping that also iterates as KEY=VALUE strings."""

    def __iter__(self):
        for key, value in self.items():
            yield f"{key}={value}"


class Container:
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

    def __getattr__(self, command: str, *args, **kwargs) -> Any:
        def command_wrapper(*args, **kwargs):
            docker_subcommand = "exec" if command == "execute" else command
            command_args = args
            if docker_subcommand == "exec" and len(args) == 1 and not kwargs:
                if isinstance(args[0], str):
                    command_args = ("sh", "-c", args[0])
                elif isinstance(args[0], (list, tuple)):
                    command_args = tuple(str(part) for part in args[0])
            full_command_args = _build_command_line(
                docker_subcommand,
                self.ID,
                *command_args,
                **kwargs,
            )

            result, command_status = asyncio.run(
                self.parent._execute_request(full_command_args=full_command_args)
            )
            exit_code = get_exit_code(result)
            result_cleaned = clean_result(result)

            if exit_code > 0:
                raise ValueError(result_cleaned)

            return result_cleaned

        if self._data and command in self._data:
            return self._data[command]

        return command_wrapper
