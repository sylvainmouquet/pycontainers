import os
import tempfile
import textwrap
import uuid

import pytest

from pycontainers import ComposeClient, ComposeService, docker
from pycontainers.features.compose.client import ComposeClient as ComposeClientType
from pycontainers.features.compose.detection import is_compose_available

compose_integration = pytest.mark.skipif(
    not is_compose_available("docker"),
    reason="docker compose is unavailable",
)


def test_compose_client_builds_project_options():
    client = ComposeClient(
        docker,
        file="docker-compose.yml",
        project_name="demo",
        project_directory="/tmp/demo",
        env_file=".env",
        profiles=["debug"],
    )
    parts = client._project_option_parts()
    assert parts == [
        "-f",
        "docker-compose.yml",
        "-p",
        "demo",
        "--project-directory",
        "/tmp/demo",
        "--env-file",
        ".env",
        "--profile",
        "debug",
    ]


def test_compose_client_builds_command():
    client = ComposeClient(docker, file="stack.yml", project_name="stack")
    command = client._build_compose_command("up", detach=True, build=True)
    assert command[:6] == ["compose", "-f", "stack.yml", "-p", "stack", "up"]
    assert set(command[6:]) == {"--detach", "--build"}


def test_compose_client_ps_adds_json_format():
    client = ComposeClient(docker)
    command = client._build_compose_command("ps")
    assert command == ["compose", "ps", "--format", "json"]


def test_compose_accessor_callable():
    client = docker.compose(file="custom.yml", project_name="custom")
    assert isinstance(client, ComposeClientType)
    assert client._file == "custom.yml"
    assert client._project_name == "custom"


def test_compose_service_repr():
    service = ComposeService(docker.compose, name="web", data={"State": "running"})
    assert repr(service) == "<ComposeService 'web' (running)>"


def test_compose_down_volumes_flag():
    client = ComposeClient(docker)
    command = client._build_compose_command("down", volumes=True, remove_orphans=True)
    assert command == [
        "compose",
        "down",
        "--remove-orphans",
        "--volumes",
    ]


@compose_integration
@pytest.mark.asyncio
async def test_compose_lifecycle_up_down_ps():
    project_name = f"pycontainers-test-{uuid.uuid4()}"
    compose_yaml = textwrap.dedent(
        """
        services:
          web:
            image: alpine:3.20
            command: ["sleep", "300"]
        """
    ).strip()

    base_tmp = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(base_tmp, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=base_tmp) as tmpdir:
        compose_file = os.path.join(tmpdir, "docker-compose.yml")
        with open(compose_file, "w") as handle:
            handle.write(compose_yaml)

        project = docker.compose(
            file=compose_file,
            project_name=project_name,
            project_directory=tmpdir,
        )

        try:
            project.up(detach=True)
            services = project.ps()
            assert len(services) == 1
            assert services[0].name == "web"

            web = project.service("web")
            output = web.exec("echo hello-compose")
            assert "hello-compose" in output

            async_services = await project.aio.ps()
            assert len(async_services) == 1
            assert async_services[0].name == "web"

            async_output = await web.aio.execute("echo async-compose")
            assert "async-compose" in async_output
        finally:
            project.down(volumes=True, remove_orphans=True)
