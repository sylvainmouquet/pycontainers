import json
from unittest.mock import AsyncMock, patch

import pytest

from pycontainers import ComposeClient, docker
from pycontainers.features.compose.client import (
    ComposeClient as ComposeClientType,
    _AsyncComposeCommandAccessor,
    _ComposeAccessor,
)
from pycontainers.shared.errors import CommandError


def test_compose_client_builds_project_options(docker_client):
    client = ComposeClient(
        docker_client,
        file="docker-compose.yml",
        project_name="demo",
        project_directory="/tmp/demo",
        env_file=".env",
        profiles=["debug"],
        invocation="plugin",
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


def test_compose_client_builds_command(docker_client):
    client = ComposeClient(
        docker_client, file="stack.yml", project_name="stack", invocation="plugin"
    )
    command = client._build_compose_command("up", detach=True, build=True)
    assert command[:6] == ["compose", "-f", "stack.yml", "-p", "stack", "up"]
    assert set(command[6:]) == {"--detach", "--build"}


def test_compose_client_builds_standalone_command(docker_client):
    client = ComposeClient(
        docker_client, file="stack.yml", project_name="stack", invocation="standalone"
    )
    command = client._build_compose_command("up", detach=True, build=True)
    assert command[:5] == ["-f", "stack.yml", "-p", "stack", "up"]
    assert set(command[5:]) == {"--detach", "--build"}


def test_compose_client_ps_adds_json_format(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    command = client._build_compose_command("ps")
    assert command == ["compose", "ps", "--format", "json"]


def test_compose_client_ps_adds_json_format_for_standalone(docker_client):
    client = ComposeClient(docker_client, invocation="standalone")
    command = client._build_compose_command("ps")
    assert command == ["ps", "--format", "json"]


def test_compose_down_volumes_flag(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    command = client._build_compose_command("down", volumes=True, remove_orphans=True)
    assert command == ["compose", "down", "--remove-orphans", "--volumes"]


def test_compose_exec_adds_non_tty_flag(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    command = client._build_compose_command("exec", "web", "echo", "hi")
    assert command == ["compose", "exec", "-T", "web", "echo", "hi"]


def test_compose_exec_keeps_tty_when_requested(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    command = client._build_compose_command(
        "exec", "web", "echo", "hi", tty=True, interactive=True
    )
    assert "-T" not in command


def test_compose_client_invocation_raises_when_unavailable(docker_client, monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.resolve_compose_invocation",
        lambda _backend: None,
    )
    client = ComposeClient(docker_client)
    with pytest.raises(RuntimeError, match="Compose is unavailable"):
        _ = client.invocation


def test_compose_client_invocation_override(docker_client):
    client = ComposeClient(docker_client, invocation="standalone")
    assert client.invocation == "standalone"


def test_compose_client_backend_property(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    assert client.backend == "docker"


def test_compose_parse_services(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    payload = json.dumps({"Service": "web", "State": "running"})
    services = client._parse_services(f"{payload}\n\n")
    assert len(services) == 1
    assert services[0].name == "web"


def test_compose_parse_services_skips_invalid_rows(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    payload = json.dumps({"State": "running"})
    assert client._parse_services(payload) == []


def test_compose_client_repr_with_details(docker_client):
    client = ComposeClient(
        docker_client,
        file="stack.yml",
        project_name="demo",
        project_directory="/tmp",
        invocation="plugin",
    )
    text = repr(client)
    assert "file='stack.yml'" in text
    assert "project_name='demo'" in text


def test_compose_client_repr_minimal(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    assert repr(client) == "<ComposeClient (docker)>"


def test_compose_accessor_callable(docker_client):
    accessor = _ComposeAccessor(docker_client)
    client = accessor(file="custom.yml", project_name="custom")
    assert isinstance(client, ComposeClientType)
    assert client._file == "custom.yml"


def test_compose_accessor_delegates_attributes(docker_client):
    accessor = _ComposeAccessor(docker_client)
    assert accessor.service("web").name == "web"
    assert isinstance(accessor.aio, _AsyncComposeCommandAccessor)
    assert "ComposeClient" in repr(accessor)


@pytest.mark.asyncio
async def test_compose_dispatch_command_success(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("done\n[exit 0]\n", 200)),
    ):
        result = await client._dispatch_command("pull", "alpine")
    assert result == "done\n"


@pytest.mark.asyncio
async def test_compose_dispatch_command_ps(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    row = json.dumps({"Service": "api", "State": "running"})
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{row}\n[exit 0]\n", 200)),
    ):
        services = await client._dispatch_command("ps")
    assert len(services) == 1
    assert services[0].name == "api"


@pytest.mark.asyncio
async def test_compose_dispatch_command_failure(docker_client):
    client = ComposeClient(docker_client, invocation="standalone")
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("failed\n[exit 1]\n", 200)),
    ):
        with pytest.raises(CommandError) as exc_info:
            await client._dispatch_command("up")
    assert exc_info.value.subcommand == "compose up"


def test_compose_sync_dispatch(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    with patch.object(
        client,
        "_dispatch_command",
        new=AsyncMock(return_value="ok"),
    ):
        assert client.up(detach=True) == "ok"


def test_compose_sync_attribute_error(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    with pytest.raises(AttributeError):
        client._undefined_private  # noqa: B018 — private names are reserved


@pytest.mark.asyncio
async def test_compose_async_accessor(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    with patch.object(
        client,
        "_dispatch_command",
        new=AsyncMock(return_value="async-ok"),
    ):
        result = await client.aio.pull("alpine")
    assert result == "async-ok"


def test_compose_global_accessor(docker_client):
    client = docker_client.compose(file="demo.yml")
    assert client._file == "demo.yml"


def test_compose_client_resolves_invocation(docker_client, monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.resolve_compose_invocation",
        lambda _backend: "plugin",
    )
    client = ComposeClient(docker_client)
    assert client.invocation == "plugin"


def test_compose_extract_project_kwargs(docker_client):
    client = ComposeClient(docker_client, invocation="plugin")
    project_kwargs, command_kwargs = client._extract_project_kwargs(
        {"file": "a.yml", "detach": True, "project_name": "demo"}
    )
    assert project_kwargs == {"file": "a.yml", "project_name": "demo"}
    assert command_kwargs == {"detach": True}


def test_compose_accessor_dynamic_command(docker_client):
    accessor = _ComposeAccessor(docker_client)
    with patch.object(
        accessor._default_client,
        "_dispatch_command",
        new=AsyncMock(return_value="ok"),
    ):
        assert accessor.up(detach=True) == "ok"
