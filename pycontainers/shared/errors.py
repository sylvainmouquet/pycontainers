"""Typed exceptions for pycontainers runtime failures."""


class PyContainersError(Exception):
    """Base exception for pycontainers."""


class UnsupportedBackendError(PyContainersError, ValueError):
    """Raised when an unsupported container runtime backend is requested."""

    def __init__(self, backend: str) -> None:
        self.backend = backend
        super().__init__(f"Unsupported backend: {backend!r}")


class CommandError(PyContainersError, ValueError):
    """Raised when a container runtime CLI command exits with a non-zero code."""

    def __init__(self, subcommand: str, exit_code: int, output: str) -> None:
        self.subcommand = subcommand
        self.exit_code = exit_code
        self.output = output
        super().__init__(
            f"{subcommand} failed with exit code {exit_code}: {output.strip()}"
        )
