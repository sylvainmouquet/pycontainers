from typing import Any
import uuid

import pytest

from pycontainers import CommandError, docker

from tests.backends.markers import requires_docker

pytestmark = requires_docker


@pytest.mark.asyncio
async def test_async_bad_command():
    with pytest.raises(CommandError) as exc_info:
        await docker.aio.run("bad-command")
    assert exc_info.value.subcommand == "run"
    assert exc_info.value.exit_code > 0


@pytest.mark.asyncio
async def test_async_docker_pull():
    result = await docker.aio.pull("ubuntu:20.04")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_async_docker_ps():
    containers = await docker.aio.ps(all=False)
    assert isinstance(containers, list)


@pytest.mark.asyncio
async def test_async_docker_run_and_execute():
    name = uuid.uuid4()
    container = await docker.aio.run(
        "alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "sleep 60"],
    )
    output = await container.aio.execute("echo 'hello world'")
    assert "hello world" in output

    list_output = await container.aio.execute(["echo", "'hello world'"])
    assert "hello world" in list_output

    await container.aio.kill()
    await container.aio.rm()

    containers = await docker.aio.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 0


@pytest.mark.asyncio
async def test_async_docker_run_with_env():
    name = uuid.uuid4()
    runtime_envs = {"VAR1": "one", "VAR2": "two"}
    container = await docker.aio.run(
        "postgres:18-alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "sleep 60"],
        envs=runtime_envs,
    )

    assert container.config.env["VAR1"] == "one"
    assert container.config.env["VAR2"] == "two"
    assert container.config.env["PG_MAJOR"] == "18"
    container_env_dict = dict[Any, Any](env.split("=") for env in container.config.env)
    assert container_env_dict["VAR1"] == "one"

    await container.aio.kill()
    await container.aio.rm()
