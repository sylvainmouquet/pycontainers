import uuid

import pytest

from pycontainers import podman
from pycontainers.shared.runtime.detection import is_runtime_available

pytestmark = pytest.mark.skipif(
    not is_runtime_available("podman"),
    reason="podman CLI is unavailable or not connected",
)


@pytest.mark.asyncio
async def test_podman_ps():
    containers = podman.ps(all=False)
    for container in containers:
        print(container)


@pytest.mark.asyncio
async def test_podman_run():
    name = uuid.uuid4()
    container = podman.run(
        "alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "sleep 30"],
    )
    containers = podman.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 1

    container.kill()
    container.rm()

    containers = podman.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 0
