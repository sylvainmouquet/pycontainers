import uuid

import pytest

from pycontainer import docker


@pytest.mark.asyncio
async def test_bad_command():
    with pytest.raises(ValueError):
        docker.run("bad-command")


@pytest.mark.asyncio
async def test_docker_pull():
    print(docker.pull("ubuntu:20.04"))


@pytest.mark.asyncio
async def test_docker_ps():
    containers = docker.ps(all=False)
    for container in containers:
        print(container)


@pytest.mark.asyncio
async def test_docker_ps_filter():
    name = uuid.uuid4()
    docker.run("ubuntu:20.04", name=name)
    containers = docker.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 1
    assert docker.rm(name) == str(name)


@pytest.mark.asyncio
async def test_docker_run():
    name = uuid.uuid4()
    docker.run(
        "ubuntu:20.04",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "echo hello world"],
    )
    containers = docker.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 1
    assert docker.rm(name) == str(name)

@pytest.mark.asyncio
async def test_docker_run_with_execute():
    name = uuid.uuid4()
    container = docker.run(
        "alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "'sleep 60s'"],
    )
    container.execute("echo 'hello world'")

    containers = docker.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 1

    container.kill()
    container.rm()

    containers = docker.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 0

@pytest.mark.asyncio
async def test_docker_run_and_kill():
    name = uuid.uuid4()
    container = docker.run(
        "alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "'sleep 60s'"],
    )
    docker.kill(container)
    docker.rm(container)
