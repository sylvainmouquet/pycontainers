from typing import Any
import uuid

import pytest

from pycontainers import CommandError, docker


@pytest.mark.asyncio
async def test_bad_command():
    with pytest.raises(CommandError) as exc_info:
        docker.run("bad-command")
    assert exc_info.value.subcommand == "run"
    assert exc_info.value.exit_code > 0


@pytest.mark.asyncio
async def test_docker_pull():
    print(docker.pull("ubuntu:20.04"))


@pytest.mark.asyncio
async def test_docker_pull_kwargs():
    print(docker.pull(command="ubuntu:20.04"))


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
        command=["-c", "sleep 60"],
    )
    container.execute("echo 'hello world'")
    container.execute(["echo", "'hello world'"])

    containers = docker.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 1

    container.kill()
    container.rm()

    containers = docker.ps(all=True, filter={"name": f"^{name}"})
    assert len(containers) == 0


@pytest.mark.asyncio
async def test_docker_run_with_env_and_instance_config_env():
    name = uuid.uuid4()
    runtime_envs = {"VAR1": "one", "VAR2": "two"}
    container = docker.run(
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

    container.kill()
    container.rm()


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


@pytest.mark.asyncio
async def test_docker_run_with_volume():
    import os
    import tempfile
    import time

    name = uuid.uuid4()
    base_tmp = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(base_tmp, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=base_tmp) as tmpdir:
        host_file = os.path.join(tmpdir, "hello.txt")
        with open(host_file, "w") as f:
            f.write("hello from host")

        container = docker.run(
            "alpine",
            name=name,
            detach=True,
            entrypoint="cp",
            command=["/data/hello.txt", "/data/from_container.txt"],
            volumes={tmpdir: {"bind": "/data", "mode": "rw"}},
        )

        from_container_path = os.path.join(tmpdir, "from_container.txt")
        timeout_seconds = 5.0
        deadline = time.time() + timeout_seconds
        while time.time() < deadline and not os.path.exists(from_container_path):
            time.sleep(0.1)

        assert os.path.exists(from_container_path)
        with open(from_container_path) as f:
            content = f.read()
        assert content == "hello from host"

        docker.rm(container)
