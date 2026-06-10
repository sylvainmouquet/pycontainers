import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from pycontainers.shared.errors import CommandError
from pycontainers.shared.runtime.container import (
    Container,
    ContainerEnv,
    _AsyncContainerCommandAccessor,
)


def test_container_env_iteration():
    env = ContainerEnv({"A": "1", "B": "2"})
    assert list(env) == ["A=1", "B=2"]


def test_container_str_uses_repr(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    assert str(container) == repr(container)


def test_container_config_from_env_dict(mock_parent):
    container = Container(
        parent=mock_parent,
        config={"env": {"KEY": "value"}},
    )
    assert container.config.env["KEY"] == "value"


def test_container_config_from_env_list(mock_parent):
    container = Container(parent=mock_parent, config={"Env": ["A=b", "flag"]})
    assert container.config.env["A"] == "b"
    assert container.config.env["flag"] == ""


def test_container_config_key_normalization(mock_parent):
    container = Container(parent=mock_parent, Config={"env": ["X=y"]})
    assert container.config.env["X"] == "y"


def test_container_data_attribute_lookup(mock_parent):
    container = Container(parent=mock_parent, data={"Publisher": "8080"}, ID="abc")
    assert container.Publisher == "8080"


def test_container_resolve_execute_string(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    subcommand, args = container._resolve_command_args("execute", ("echo hi",), {})
    assert subcommand == "exec"
    assert args == ("sh", "-c", "echo hi")


def test_container_resolve_execute_sequence(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    subcommand, args = container._resolve_command_args(
        "execute", (["echo", "hi"],), {}
    )
    assert args == ("echo", "hi")


@pytest.mark.asyncio
async def test_container_dispatch_command_success(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    mock_parent.execute_responses = [("output\n[exit 0]\n", 200)]
    result = await container._dispatch_command("logs")
    assert result == "output\n"


@pytest.mark.asyncio
async def test_container_dispatch_command_failure(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    mock_parent.execute_responses = [("failed\n[exit 3]\n", 200)]
    with pytest.raises(CommandError) as exc_info:
        await container._dispatch_command("logs")
    assert exc_info.value.exit_code == 3


@pytest.mark.asyncio
async def test_container_dispatch_stream(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    mock_parent.stream_chunks = ["chunk-a", "chunk-b\n[exit 0]\n"]

    chunks = [chunk async for chunk in container._dispatch_stream("logs")]
    assert chunks == ["chunk-a", "chunk-b\n[exit 0]\n"]


@pytest.mark.asyncio
async def test_container_dispatch_stream_lines(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    mock_parent.stream_chunks = ["line-one\n", "line-two\n[exit 0]\n"]

    lines = [line async for line in container._dispatch_stream_lines("logs")]
    assert lines == ["line-one", "line-two", "[exit 0]"]


def test_container_sync_stream_helpers(mock_parent):
    container = Container(parent=mock_parent, ID="abc")

    def make_chunks():
        async def chunks() -> AsyncIterator[str]:
            yield "chunk-one\n"
            yield "chunk-two\n[exit 0]\n"

        return chunks()

    with patch.object(
        container, "_dispatch_stream", side_effect=lambda *args, **kwargs: make_chunks()
    ):
        assert list(container.stream("logs")) == ["chunk-one\n", "chunk-two\n[exit 0]\n"]
        assert list(container.stream_lines("logs")) == [
            "chunk-one",
            "chunk-two",
            "[exit 0]",
        ]
        assert list(container.follow_logs()) == ["chunk-one", "chunk-two", "[exit 0]"]


def test_container_sync_command(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    with patch.object(
        container,
        "_dispatch_command",
        new=AsyncMock(return_value="done"),
    ):
        assert container.logs() == "done"


def test_container_logs_follow(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    with patch.object(
        container,
        "_sync_stream_lines",
        return_value=iter(["live"]),
    ):
        assert list(container.logs(follow=True)) == ["live"]


@pytest.mark.asyncio
async def test_container_async_accessor(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    accessor = _AsyncContainerCommandAccessor(container)
    with patch.object(
        container,
        "_dispatch_command",
        new=AsyncMock(return_value="exec-output"),
    ):
        assert await accessor.execute("echo hi") == "exec-output"

    with patch.object(
        container,
        "_dispatch_command",
        new=AsyncMock(return_value="stopped"),
    ):
        assert await accessor.stop() == "stopped"


@pytest.mark.asyncio
async def test_container_async_accessor_streaming(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    accessor = _AsyncContainerCommandAccessor(container)

    async def chunks():
        yield "chunk\n[exit 0]\n"

    with patch.object(container, "_dispatch_stream", return_value=chunks()):
        stream_chunks = [chunk async for chunk in accessor.stream("logs")]
        assert stream_chunks == ["chunk\n[exit 0]\n"]

    with patch.object(container, "_dispatch_stream_lines", return_value=chunks()):
        lines = [line async for line in accessor.stream_lines("logs")]
        assert lines == ["chunk\n[exit 0]\n"]

    with patch.object(container, "_dispatch_stream_lines", return_value=chunks()):
        follow = [line async for line in accessor.follow_logs()]
        assert follow == ["chunk\n[exit 0]\n"]


def test_container_config_preserves_container_env(mock_parent):
    env = ContainerEnv({"KEY": "value"})
    container = Container(parent=mock_parent, config={"env": env})
    assert container.config.env is env
    container = Container(parent=mock_parent, config={"env": {"KEY": "value"}})
    assert isinstance(container.config.env, ContainerEnv)


def test_container_resolve_execute_list(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    subcommand, args = container._resolve_command_args(
        "execute", (["echo", "hi"],), {}
    )
    assert args == ("echo", "hi")


def test_container_resolve_execute_tuple(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    subcommand, args = container._resolve_command_args(
        "execute", (("echo", "hi"),), {}
    )
    assert args == ("echo", "hi")


def test_container_resolve_execute_with_kwargs(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    subcommand, args = container._resolve_command_args(
        "execute", ("echo hi",), {"user": "root"}
    )
    assert subcommand == "exec"
    assert args == ("echo hi",)


def test_container_aio_property(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    assert isinstance(container.aio, _AsyncContainerCommandAccessor)


def test_container_dynamic_attribute_from_data(mock_parent):
    container = Container(
        parent=mock_parent,
        data={"Command": "sleep 60"},
        ID="abc",
    )
    assert container.Command == "sleep 60"


def test_container_getattr_reads_data_without_setattr(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    container._data = {"OnlyInData": "yes"}
    assert container.OnlyInData == "yes"


def test_container_dynamic_rm(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    with patch.object(
        container,
        "_dispatch_command",
        new=AsyncMock(return_value="removed"),
    ):
        assert container.rm() == "removed"


def test_container_attribute_error(mock_parent):
    container = Container(parent=mock_parent, ID="abc")
    with pytest.raises(AttributeError):
        container._undefined_private  # noqa: B018 — private names are reserved
