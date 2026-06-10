import shutil
import subprocess
import sys
from typing import Literal

RuntimeBackend = Literal["docker", "podman"]


def detect_runtime() -> RuntimeBackend:
    """Return the first available container runtime CLI on PATH."""
    if shutil.which("docker") is not None:
        return "docker"
    if shutil.which("podman") is not None:
        return "podman"
    raise RuntimeError("No container runtime found: install docker or podman")


def is_runtime_available(backend: RuntimeBackend) -> bool:
    """Return True when the requested runtime CLI responds successfully."""
    if shutil.which(backend) is None:
        return False

    result = subprocess.run(
        [backend, "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def resolve_docker_command_backend() -> str | None:
    """Return the CLI binary used for the docker backend, if any is connected."""
    if sys.platform == "darwin":
        if is_runtime_available("docker"):
            return "docker"
        from pycontainers.shared.runtime.macos_commands import (
            is_macos_container_available,
        )

        if is_macos_container_available():
            return "container"
        return None
    if is_runtime_available("docker"):
        return "docker"
    return None


def is_docker_available() -> bool:
    """Return True when docker-backed integration tests can run on this host."""
    return resolve_docker_command_backend() is not None
