from typing import TYPE_CHECKING, Any

from pycontainers.shared.logging import get_logger

if TYPE_CHECKING:
    from pycontainers.features.compose.client import ComposeClient

logger = get_logger(__name__)


class _AsyncServiceCommandAccessor:
    """Async dynamic dispatch for compose service-scoped subcommands."""

    def __init__(self, service: "ComposeService") -> None:
        self._service = service

    async def execute(self, *args, **kwargs) -> str:
        return await self._service._dispatch_command("exec", *args, **kwargs)

    def __getattr__(self, subcommand: str):
        async def command_wrapper(*args, **kwargs):
            return await self._service._dispatch_command(subcommand, *args, **kwargs)

        return command_wrapper


class ComposeService:
    """Accessor for a single service inside a compose project."""

    _NON_COMMAND_ATTRS = frozenset({"aio", "compose", "name", "_data"})

    def __init__(
        self,
        compose: "ComposeClient",
        name: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.compose = compose
        self.name = name
        self._data = data or {}

        if data is not None:
            for key, value in data.items():
                setattr(self, key, value)

    def _resolve_command_args(
        self, subcommand: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[str, tuple[Any, ...]]:
        command_args = args
        if subcommand == "exec" and len(args) == 1 and not kwargs:
            if isinstance(args[0], str):
                command_args = ("sh", "-c", args[0])
            elif isinstance(args[0], (list, tuple)):
                command_args = tuple(str(part) for part in args[0])
        return subcommand, (self.name, *command_args)

    async def _dispatch_command(self, subcommand: str, *args, **kwargs) -> str:
        runtime_subcommand, command_args = self._resolve_command_args(
            subcommand, args, kwargs
        )
        return await self.compose._dispatch_command(
            runtime_subcommand, *command_args, **kwargs
        )

    @property
    def aio(self) -> _AsyncServiceCommandAccessor:
        """Async-first dispatch for service-scoped compose commands."""
        return _AsyncServiceCommandAccessor(self)

    def __getattr__(self, subcommand: str) -> Any:
        if self._data and subcommand in self._data:
            return self._data[subcommand]

        if subcommand in self._NON_COMMAND_ATTRS or subcommand.startswith("_"):
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {subcommand!r}"
            )

        def command_wrapper(*args, **kwargs):
            return self.compose.parent._run_sync(
                self._dispatch_command(subcommand, *args, **kwargs)
            )

        return command_wrapper

    def __repr__(self) -> str:
        state = getattr(self, "State", None) or getattr(self, "Status", None)
        if state:
            return f"<ComposeService {self.name!r} ({state})>"
        return f"<ComposeService {self.name!r}>"
