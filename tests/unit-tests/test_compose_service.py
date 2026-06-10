from unittest.mock import AsyncMock, patch

import pytest

from pycontainers.features.compose.client import ComposeClient
from pycontainers.features.compose.service import (
    ComposeService,
    _AsyncServiceCommandAccessor,
)


def test_compose_service_stores_data(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web", data={"State": "running"})
    assert service.name == "web"
    assert service.State == "running"


def test_compose_service_repr_with_state(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web", data={"State": "running"})
    assert repr(service) == "<ComposeService 'web' (running)>"


def test_compose_service_repr_without_state(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web", data={"State": "", "Status": ""})
    assert repr(service) == "<ComposeService 'web'>"


def test_compose_service_data_attribute_lookup(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web", data={"Publisher": "8080"})
    assert service.Publisher == "8080"


def test_compose_service_resolve_exec_string(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    subcommand, args = service._resolve_command_args("exec", ("echo hi",), {})
    assert subcommand == "exec"
    assert args == ("web", "sh", "-c", "echo hi")


def test_compose_service_resolve_exec_sequence(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    subcommand, args = service._resolve_command_args("exec", (["echo", "hi"],), {})
    assert args == ("web", "echo", "hi")


@pytest.mark.asyncio
async def test_compose_service_dispatch_delegates(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    with patch.object(
        compose,
        "_dispatch_command",
        new=AsyncMock(return_value="done"),
    ) as dispatch:
        result = await service._dispatch_command("logs")
    dispatch.assert_awaited_once_with("logs", "web")
    assert result == "done"


def test_compose_service_sync_command(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    with patch.object(
        service,
        "_dispatch_command",
        new=AsyncMock(return_value="sync"),
    ):
        assert service.logs() == "sync"


@pytest.mark.asyncio
async def test_compose_service_async_accessor(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    with patch.object(
        service,
        "_dispatch_command",
        new=AsyncMock(return_value="async"),
    ):
        result = await service.aio.execute("echo hi")
    assert result == "async"


@pytest.mark.asyncio
async def test_compose_service_async_dynamic_command(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    with patch.object(
        service,
        "_dispatch_command",
        new=AsyncMock(return_value="scaled"),
    ):
        assert await service.aio.logs() == "scaled"


def test_compose_service_resolve_exec_with_kwargs(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    subcommand, args = service._resolve_command_args(
        "exec", ("echo hi",), {"interactive": True}
    )
    assert args == ("web", "echo hi")


def test_compose_service_resolve_exec_list(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    subcommand, args = service._resolve_command_args("exec", (["echo", "hi"],), {})
    assert args == ("web", "echo", "hi")


def test_compose_service_resolve_exec_tuple(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    subcommand, args = service._resolve_command_args("exec", (("echo", "hi"),), {})
    assert args == ("web", "echo", "hi")


def test_compose_service_resolve_non_exec_sequence_unchanged(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    subcommand, args = service._resolve_command_args("logs", (["tail"],), {})
    assert subcommand == "logs"
    assert args == ("web", ["tail"])


def test_compose_service_getattr_reads_data_without_setattr(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    service._data = {"OnlyInData": "yes"}
    assert service.OnlyInData == "yes"


def test_compose_service_sync_dynamic_command(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    with patch.object(
        service,
        "_dispatch_command",
        new=AsyncMock(return_value="restarted"),
    ):
        assert service.restart() == "restarted"


def test_compose_service_attribute_error(docker_client):
    compose = ComposeClient(docker_client, invocation="plugin")
    service = ComposeService(compose, name="web")
    with pytest.raises(AttributeError):
        service._undefined_private  # noqa: B018 — private names are reserved
