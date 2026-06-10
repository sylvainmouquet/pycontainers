import sys
import uuid

import pytest

from pycontainers import CommandError, docker

from tests.backends.markers import requires_container

pytestmark = [
    requires_container,
    pytest.mark.skipif(
        sys.platform != "darwin",
        reason="Apple container CLI integration tests run only on macOS",
    ),
]


def _containers_named(containers: list, name: uuid.UUID) -> list:
    name_str = str(name)
    return [
        container
        for container in containers
        if name_str in str(container.get("Names", ""))
        or name_str in str(container.get("ID", ""))
    ]


@pytest.mark.asyncio
async def test_bad_command():
    with pytest.raises(CommandError) as exc_info:
        docker.run("bad-command")
    assert exc_info.value.subcommand == "run"
    assert exc_info.value.exit_code > 0


def test_container_ps():
    containers = docker.ps(all=False)
    assert isinstance(containers, list)


def test_container_ps_all():
    containers = docker.ps(all=True)
    assert isinstance(containers, list)


@pytest.mark.asyncio
async def test_container_run_and_cleanup():
    name = uuid.uuid4()
    container = docker.run(
        "alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "sleep 30"],
    )
    containers = _containers_named(docker.ps(all=True), name)
    assert len(containers) >= 1

    container.kill()
    container.rm()

    containers = _containers_named(docker.ps(all=True), name)
    assert len(containers) == 0
