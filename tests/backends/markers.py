import pytest

from pycontainers.shared.runtime.detection import (
    is_docker_available,
    is_runtime_available,
)
from pycontainers.shared.runtime.macos_commands import is_macos_container_available

requires_docker = pytest.mark.skipif(
    not is_docker_available(),
    reason="docker backend is unavailable or not connected",
)

requires_container = pytest.mark.skipif(
    not is_macos_container_available(),
    reason="Apple container CLI is unavailable or not connected",
)

requires_podman = pytest.mark.skipif(
    not is_runtime_available("podman"),
    reason="podman CLI is unavailable or not connected",
)