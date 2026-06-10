import shutil
import subprocess
from typing import Literal

from pycontainers.shared.logging import get_logger
from pycontainers.shared.runtime.detection import RuntimeBackend
from pycontainers.shared.runtime.macos_commands import uses_macos_container_cli

logger = get_logger(__name__)

ComposeInvocation = Literal["plugin", "standalone"]


def _compose_plugin_available(backend: RuntimeBackend) -> bool:
    if shutil.which(backend) is None:
        return False

    result = subprocess.run(
        [backend, "compose", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _standalone_compose_binary(backend: RuntimeBackend) -> str | None:
    binary = f"{backend}-compose"
    if shutil.which(binary) is None:
        return None

    result = subprocess.run(
        [binary, "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return binary if result.returncode == 0 else None


def resolve_compose_invocation(
    backend: RuntimeBackend = "docker",
) -> ComposeInvocation | None:
    """Return how compose commands should be invoked for the given backend."""
    if uses_macos_container_cli(backend):
        logger.debug(
            "Compose unavailable for macOS container CLI",
            backend=backend,
        )
        return None
    if _compose_plugin_available(backend):
        logger.debug("Resolved compose invocation", backend=backend, invocation="plugin")
        return "plugin"
    standalone = _standalone_compose_binary(backend)
    if standalone is not None:
        logger.debug(
            "Resolved compose invocation",
            backend=backend,
            invocation="standalone",
            binary=standalone,
        )
        return "standalone"
    logger.warning("Compose is unavailable", backend=backend)
    return None


def resolve_compose_endpoint(
    backend: RuntimeBackend,
    invocation: ComposeInvocation,
) -> str:
    """Return the ProxyCraft endpoint used to execute compose commands."""
    if invocation == "plugin":
        return f"/{backend}"
    return f"/{backend}-compose"


def is_compose_available(backend: RuntimeBackend = "docker") -> bool:
    """Return True when compose can run via plugin or standalone CLI."""
    return resolve_compose_invocation(backend) is not None
