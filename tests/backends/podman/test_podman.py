import uuid

import pytest

from pycontainers import podman

from tests.backends.markers import requires_podman

pytestmark = requires_podman


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
