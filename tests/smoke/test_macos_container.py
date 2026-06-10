import sys

import pytest

from pycontainers import docker
from pycontainers.shared.runtime.macos_commands import is_macos_container_available


pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="Apple container CLI smoke tests run only on macOS",
)


@pytest.mark.skipif(
    not is_macos_container_available(),
    reason="Apple container CLI is not installed or the daemon is unavailable",
)
def test_macos_container_ps_smoke():
    containers = docker.ps(all=False)
    assert isinstance(containers, list)


@pytest.mark.skipif(
    not is_macos_container_available(),
    reason="Apple container CLI is not installed or the daemon is unavailable",
)
def test_macos_container_ps_all_smoke():
    containers = docker.ps(all=True)
    assert isinstance(containers, list)
