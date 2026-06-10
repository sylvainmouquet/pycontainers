import asyncio
import concurrent.futures
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pycontainers import CommandError, docker, podman
from pycontainers.shared.runtime.client import (
    PyContainers,
    _AsyncCommandAccessor,
    _configuration_for_backend,
)
from pycontainers.shared.runtime.container import Container, ContainerEnv


def test_configuration_for_backend_non_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    config = _configuration_for_backend("docker")
    docker_endpoint = next(
        endpoint for endpoint in config["endpoints"] if endpoint["identifier"] == "/docker"
    )
    assert docker_endpoint["backends"]["command"]["darwin"] == "container"
    assert docker_endpoint["backends"]["command"]["linux"] == "docker"


def test_configuration_for_backend_darwin_container(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.resolve_docker_command_backend",
        lambda: "container",
    )
    config = _configuration_for_backend("docker")
    docker_endpoint = next(
        endpoint for endpoint in config["endpoints"] if endpoint["identifier"] == "/docker"
    )
    assert docker_endpoint["backends"]["command"]["darwin"] == "container"


def test_configuration_for_backend_darwin_no_backend(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.resolve_docker_command_backend",
        lambda: None,
    )
    config = _configuration_for_backend("docker")
    assert config["endpoints"][0]["backends"]["command"]["darwin"] == "container"


@pytest.mark.asyncio
async def test_pycontainers_uses_running_event_loop():
    client = PyContainers(backend="docker")
    assert client.loop is asyncio.get_running_loop()
    assert client.startup_task is not None
    await client.close()


@pytest.mark.asyncio
async def test_sync_dispatch_from_async_context(docker_client):
    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value=[]),
    ):
        assert docker_client.ps() == []


def test_run_sync_uses_existing_stopped_loop():
    client = PyContainers.__new__(PyContainers)
    client._owns_background_loop = False
    client.loop = asyncio.new_event_loop()

    async def value():
        return "ok"

    try:
        assert client._run_sync(value()) == "ok"
    finally:
        client.loop.close()


@pytest.mark.asyncio
async def test_run_sync_uses_thread_from_async_context():
    client = PyContainers.__new__(PyContainers)
    client._owns_background_loop = False
    client.loop = asyncio.get_running_loop()

    async def value():
        return "ok"

    assert client._run_sync(value()) == "ok"


@pytest.mark.asyncio
async def test_session_client_non_stream_mode():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = "plain response"

    class ClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch("pycontainers.shared.runtime.client.httpx.AsyncClient", return_value=ClientContext()):
        responses = [
            response
            async for response in docker._session_client(
                app=docker.proxycraft.app,
                method="GET",
                stream=False,
                payload={"args": ["version"]},
                endpoint="/docker",
            )
        ]

    assert len(responses) == 1
    assert responses[0].text == "plain response"


@pytest.mark.asyncio
async def test_load_env_from_inspect_success(docker_client):
    inspect_payload = json.dumps([{"Config": {"Env": ["FOO=bar", "BAZ=qux"]}}])
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{inspect_payload}\n[exit 0]\n", 200)),
    ):
        env = await docker_client._load_env_from_inspect("abc123")
    assert env == {"FOO": "bar", "BAZ": "qux"}


@pytest.mark.asyncio
async def test_load_env_from_inspect_dict_payload(docker_client):
    inspect_payload = json.dumps({"Config": {"Env": ["ONE=two"]}})
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{inspect_payload}\n[exit 0]\n", 200)),
    ):
        env = await docker_client._load_env_from_inspect("abc123")
    assert env == {"ONE": "two"}


@pytest.mark.asyncio
async def test_load_env_from_inspect_non_zero_exit(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("missing\n[exit 1]\n", 200)),
    ):
        assert await docker_client._load_env_from_inspect("abc123") is None


@pytest.mark.asyncio
async def test_load_env_from_inspect_empty_result(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("[exit 0]\n", 200)),
    ):
        assert await docker_client._load_env_from_inspect("abc123") is None


@pytest.mark.asyncio
async def test_load_env_from_inspect_invalid_config(docker_client):
    payload = json.dumps([{"Config": "invalid"}])
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{payload}\n[exit 0]\n", 200)),
    ):
        assert await docker_client._load_env_from_inspect("abc123") is None


@pytest.mark.asyncio
async def test_load_env_from_exec_success(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("FOO=bar\n[exit 0]\n", 200)),
    ):
        env = await docker_client._load_env_from_exec("abc123")
    assert env == {"FOO": "bar"}


@pytest.mark.asyncio
async def test_load_env_from_exec_failure(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("denied\n[exit 1]\n", 200)),
    ):
        assert await docker_client._load_env_from_exec("abc123") is None


@pytest.mark.asyncio
async def test_build_run_container_uses_runtime_envs(docker_client):
    with patch.object(
        docker_client,
        "_load_env_from_inspect",
        new=AsyncMock(return_value=None),
    ), patch.object(
        docker_client,
        "_load_env_from_exec",
        new=AsyncMock(return_value=None),
    ):
        container = await docker_client._build_run_container(
            "abc123", {"RUNTIME": "value"}
        )
    assert container.ID == "abc123"
    assert container.config.env["RUNTIME"] == "value"


@pytest.mark.asyncio
async def test_build_run_container_handles_inspect_exception(docker_client):
    with patch.object(
        docker_client,
        "_load_env_from_inspect",
        new=AsyncMock(side_effect=RuntimeError("inspect failed")),
    ), patch.object(
        docker_client,
        "_load_env_from_exec",
        new=AsyncMock(return_value=ContainerEnv({"FROM": "exec"})),
    ):
        container = await docker_client._build_run_container("abc123", None)
    assert container.config.env["FROM"] == "exec"


@pytest.mark.asyncio
async def test_build_run_container_handles_exec_exception(docker_client):
    with patch.object(
        docker_client,
        "_load_env_from_inspect",
        new=AsyncMock(return_value=None),
    ), patch.object(
        docker_client,
        "_load_env_from_exec",
        new=AsyncMock(side_effect=RuntimeError("exec failed")),
    ):
        container = await docker_client._build_run_container("abc123", None)
    assert container.config is None


def test_prepare_command_args_macos(docker_client, monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.uses_macos_container_cli",
        lambda _backend: True,
    )
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.adapt_command_line_for_macos",
        lambda parts: ["list"],
    )
    assert docker_client._prepare_command_args("ps") == ["list"]


@pytest.mark.asyncio
async def test_dispatch_command_run(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("container-id\n[exit 0]\n", 200)),
    ), patch.object(
        docker_client,
        "_build_run_container",
        new=AsyncMock(return_value=Container(parent=docker_client, ID="container-id")),
    ) as build_container:
        container = await docker_client._dispatch_command("run", "alpine")
    build_container.assert_awaited_once_with("container-id", None)
    assert container.ID == "container-id"


@pytest.mark.asyncio
async def test_dispatch_command_run_podman_pull_output(docker_client):
    run_output = (
        'Resolved "alpine" as an alias\r\n'
        "Writing manifest to image destination\r\n"
        "abc123containerid\r\n[exit 0]\n"
    )
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(run_output, 200)),
    ), patch.object(
        docker_client,
        "_build_run_container",
        new=AsyncMock(return_value=Container(parent=docker_client, ID="abc123containerid")),
    ) as build_container:
        container = await docker_client._dispatch_command("run", "alpine")
    build_container.assert_awaited_once_with("abc123containerid", None)
    assert container.ID == "abc123containerid"


@pytest.mark.asyncio
async def test_dispatch_command_ps_docker(docker_client, monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.uses_macos_container_cli",
        lambda _backend: False,
    )
    row = json.dumps({"ID": "abc", "Names": "demo"})
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{row}\n[exit 0]\n", 200)),
    ):
        containers = await docker_client._dispatch_command("ps")
    assert len(containers) == 1
    assert containers[0].ID == "abc"


@pytest.mark.asyncio
async def test_dispatch_command_ps_podman_array(docker_client, monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.uses_macos_container_cli",
        lambda _backend: False,
    )
    payload = json.dumps([{"ID": "abc", "Names": "demo"}])
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{payload}\n[exit 0]\n", 200)),
    ):
        containers = await docker_client._dispatch_command("ps")
    assert len(containers) == 1
    assert containers[0].ID == "abc"


@pytest.mark.asyncio
async def test_dispatch_command_ps_macos(docker_client, monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.uses_macos_container_cli",
        lambda _backend: True,
    )
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.parse_macos_container_list",
        lambda _result: [{"ID": "mac", "Names": "mac"}],
    )
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("[]\n[exit 0]\n", 200)),
    ):
        containers = await docker_client._dispatch_command("ps")
    assert containers[0].ID == "mac"


@pytest.mark.asyncio
async def test_dispatch_command_failure(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("failed\n[exit 2]\n", 200)),
    ):
        with pytest.raises(CommandError) as exc_info:
            await docker_client._dispatch_command("pull", "missing")
    assert exc_info.value.exit_code == 2


@pytest.mark.asyncio
async def test_dispatch_command_generic_success(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("pulled\n[exit 0]\n", 200)),
    ):
        result = await docker_client._dispatch_command("pull", "alpine")
    assert result == "pulled\n"


@pytest.mark.asyncio
async def test_stream_command_exception(docker_client):
    async def failing_iter(*args, **kwargs):
        raise RuntimeError("stream failed")
        yield ""  # pragma: no cover

    with patch.object(docker_client, "_iter_request", side_effect=failing_iter):
        with pytest.raises(RuntimeError, match="stream failed"):
            async for _ in docker_client._stream_command("logs", ["logs", "demo"]):
                pass


@pytest.mark.asyncio
async def test_dispatch_stream_lines(docker_client):
    async def chunks():
        yield "line-one\n"
        yield "line-two\n[exit 0]\n"

    with patch.object(docker_client, "_dispatch_stream", return_value=chunks()):
        lines = [line async for line in docker_client._dispatch_stream_lines("logs")]
    assert lines == ["line-one", "line-two", "[exit 0]"]


def test_sync_stream_helpers(docker_client):
    def make_chunks():
        async def chunks():
            yield "chunk-one\n"
            yield "chunk-two\n[exit 0]\n"

        return chunks()

    with patch.object(
        docker_client, "_dispatch_stream", side_effect=lambda *args, **kwargs: make_chunks()
    ):
        assert list(docker_client.stream("logs", "demo")) == [
            "chunk-one\n",
            "chunk-two\n[exit 0]\n",
        ]
        assert list(docker_client.stream_lines("logs", "demo")) == [
            "chunk-one",
            "chunk-two",
            "[exit 0]",
        ]
        assert list(docker_client.follow_logs("demo")) == [
            "chunk-one",
            "chunk-two",
            "[exit 0]",
        ]


def test_sync_run_ps_pull(docker_client):
    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(side_effect=["pulled", [Container(parent=docker_client, ID="x")], Container(parent=docker_client, ID="y")]),
    ):
        assert docker_client.pull("alpine") == "pulled"
        assert docker_client.ps()[0].ID == "x"
        assert docker_client.run("alpine").ID == "y"


def test_pull_requires_image_or_command(docker_client):
    with pytest.raises(TypeError, match="pull\\(\\) requires"):
        docker_client.pull()


@pytest.mark.asyncio
async def test_async_accessor_methods(docker_client):
    accessor = _AsyncCommandAccessor(docker_client)
    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value=Container(parent=docker_client, ID="run-id")),
    ):
        container = await accessor.run("alpine")
        assert container.ID == "run-id"

    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value=[]),
    ):
        assert await accessor.ps() == []

    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value="pulled"),
    ):
        assert await accessor.pull("alpine") == "pulled"

    with patch.object(
        docker_client,
        "_dispatch_stream",
        return_value=_async_gen(["chunk"]),
    ):
        chunks = [chunk async for chunk in accessor.stream("logs")]
        assert chunks == ["chunk"]

    with patch.object(
        docker_client,
        "_dispatch_stream_lines",
        return_value=_async_gen(["line"]),
    ):
        lines = [line async for line in accessor.follow_logs()]
        assert lines == ["line"]

    with pytest.raises(TypeError, match="pull\\(\\) requires"):
        await accessor.pull()


@pytest.mark.asyncio
async def test_async_accessor_dynamic_command(docker_client):
    accessor = _AsyncCommandAccessor(docker_client)
    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value="stopped"),
    ):
        stop = accessor.stop
        assert await stop("demo") == "stopped"


def test_pycontainers_compose_property(docker_client):
    assert docker_client.compose.service("web").name == "web"


def test_pycontainers_dynamic_logs_follow(docker_client):
    with patch.object(
        docker_client,
        "_sync_stream_lines",
        return_value=iter(["live"]),
    ):
        assert list(docker_client.logs("demo", follow=True)) == ["live"]


def test_pycontainers_dynamic_command(docker_client):
    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value="removed"),
    ):
        assert docker_client.rm("demo") == "removed"


def test_pycontainers_attribute_error_for_reserved_name(docker_client):
    with pytest.raises(AttributeError):
        docker_client._undefined_private  # noqa: B018 — private names are reserved


@pytest.mark.asyncio
async def test_execute_request_success_logging(docker_client):
    mock_response = MagicMock()
    mock_response.text = "ok\n[exit 0]\n"
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    async def session(*args, **kwargs):
        yield mock_response

    with patch.object(docker_client, "_session_client", side_effect=session):
        text, status = await docker_client._execute_request(["version"])
    assert text.startswith("ok")
    assert status == 200


@pytest.mark.asyncio
async def test_close_client(docker_client):
    await docker_client.close()


def test_cleanup_sync_success():
    loop = asyncio.new_event_loop()
    proxy = MagicMock()
    proxy.shutdown_event = AsyncMock(return_value=None)
    PyContainers._cleanup_sync(proxy, loop, None, False)
    assert loop.is_closed()


def test_cleanup_sync_timeout_does_not_warn(capsys):
    loop = asyncio.new_event_loop()
    proxy = MagicMock()
    proxy.shutdown_event = AsyncMock(side_effect=concurrent.futures.TimeoutError())

    PyContainers._cleanup_sync(proxy, loop, None, False)

    captured = capsys.readouterr().out
    assert "Runtime client cleanup failed" not in captured
    loop.close()


def test_shutdown_sync_is_idempotent():
    client = PyContainers.__new__(PyContainers)
    client._shutdown_done = True
    client.loop = MagicMock()
    client._shutdown_sync()
    client.loop.is_closed.assert_not_called()


def test_shutdown_sync_background_loop_handles_shutdown_error():
    client = PyContainers.__new__(PyContainers)
    client._shutdown_done = False
    client._owns_background_loop = True
    client.loop = MagicMock()
    client.loop.is_closed.return_value = False
    client.loop.is_running.return_value = True
    client.proxycraft = MagicMock()
    client.proxycraft.shutdown_event = MagicMock(return_value=object())
    loop_thread = MagicMock()
    client._loop_thread = loop_thread
    future = MagicMock()
    future.result.side_effect = RuntimeError("timeout")

    with patch(
        "pycontainers.shared.runtime.client.asyncio.run_coroutine_threadsafe",
        return_value=future,
    ):
        client._shutdown_sync()

    client.loop.call_soon_threadsafe.assert_called_once_with(client.loop.stop)
    loop_thread.join.assert_called_once_with(timeout=1)
    assert client._loop_thread is None


def test_shutdown_sync_stopped_loop_handles_shutdown_error():
    client = PyContainers.__new__(PyContainers)
    client._shutdown_done = False
    client._owns_background_loop = False
    client.loop = MagicMock()
    client.loop.is_closed.return_value = False
    client.loop.is_running.return_value = False
    client.loop.run_until_complete.side_effect = RuntimeError("shutdown failed")
    client.proxycraft = MagicMock()
    client.proxycraft.shutdown_event = MagicMock(return_value=object())

    client._shutdown_sync()

    client.loop.close.assert_called_once()


def test_cleanup_sync_closed_loop_returns():
    loop = MagicMock()
    loop.is_closed.return_value = True
    proxy = MagicMock()

    PyContainers._cleanup_sync(proxy, loop, None, False)

    proxy.shutdown_event.assert_not_called()


def test_cleanup_sync_running_unowned_loop_returns():
    loop = MagicMock()
    loop.is_closed.return_value = False
    loop.is_running.return_value = True
    proxy = MagicMock()

    PyContainers._cleanup_sync(proxy, loop, None, False)

    proxy.shutdown_event.assert_not_called()


def test_cleanup_sync_background_inner_error_stops_loop():
    loop = MagicMock()
    loop.is_closed.return_value = False
    loop.is_running.return_value = True
    proxy = MagicMock()
    proxy.shutdown_event = MagicMock(return_value=object())
    loop_thread = MagicMock()

    with patch(
        "pycontainers.shared.runtime.client.asyncio.run_coroutine_threadsafe",
        side_effect=RuntimeError("submit failed"),
    ):
        PyContainers._cleanup_sync(proxy, loop, loop_thread, True)

    loop.call_soon_threadsafe.assert_called_once_with(loop.stop)
    loop_thread.join.assert_called_once_with(timeout=1)


def test_cleanup_sync_timeout_outer_branch_stops_loop():
    loop = MagicMock()
    loop.is_closed.return_value = False
    loop.is_running.side_effect = [concurrent.futures.TimeoutError(), True]
    proxy = MagicMock()
    loop_thread = MagicMock()

    PyContainers._cleanup_sync(proxy, loop, loop_thread, True)

    loop.call_soon_threadsafe.assert_called_once_with(loop.stop)
    loop_thread.join.assert_called_once_with(timeout=1)


def test_cleanup_sync_generic_outer_branch_stops_loop():
    loop = MagicMock()
    loop.is_closed.return_value = False
    loop.is_running.side_effect = [RuntimeError("state failed"), True]
    proxy = MagicMock()
    loop_thread = MagicMock()

    PyContainers._cleanup_sync(proxy, loop, loop_thread, True)

    loop.call_soon_threadsafe.assert_called_once_with(loop.stop)
    loop_thread.join.assert_called_once_with(timeout=1)


def test_package_level_clients_exist():
    assert docker.backend == "docker"
    assert podman.backend == "podman"


@pytest.mark.asyncio
async def test_load_env_from_inspect_empty_parsed_list(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("[]\n[exit 0]\n", 200)),
    ):
        assert await docker_client._load_env_from_inspect("abc123") is None


@pytest.mark.asyncio
async def test_load_env_from_inspect_env_not_list(docker_client):
    payload = json.dumps({"Config": {"Env": "invalid"}})
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=(f"{payload}\n[exit 0]\n", 200)),
    ):
        assert await docker_client._load_env_from_inspect("abc123") is None


@pytest.mark.asyncio
async def test_load_env_from_exec_empty_output(docker_client):
    with patch.object(
        docker_client,
        "_execute_request",
        new=AsyncMock(return_value=("[exit 0]\n", 200)),
    ):
        assert await docker_client._load_env_from_exec("abc123") is None


@pytest.mark.asyncio
async def test_build_run_container_uses_inspect_env(docker_client):
    with patch.object(
        docker_client,
        "_load_env_from_inspect",
        new=AsyncMock(return_value=ContainerEnv({"FROM": "inspect"})),
    ):
        container = await docker_client._build_run_container("abc123", None)
    assert container.config.env["FROM"] == "inspect"


def test_configuration_for_backend_updates_docker_endpoint(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.resolve_docker_command_backend",
        lambda: "container",
    )
    config = _configuration_for_backend("docker")
    docker_endpoint = next(
        endpoint for endpoint in config["endpoints"] if endpoint["identifier"] == "/docker"
    )
    assert docker_endpoint["backends"]["command"]["darwin"] == "container"


def test_configuration_for_backend_without_docker_endpoint(monkeypatch):
    from pycontainers.shared.runtime.config import PODMAN_ENDPOINT

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.resolve_docker_command_backend",
        lambda: "container",
    )
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.CONFIGURATION",
        {
            "version": "1.0",
            "name": "PyContainers",
            "server": {"type": "local"},
            "endpoints": [PODMAN_ENDPOINT],
        },
    )
    config = _configuration_for_backend("docker")
    assert all(
        endpoint["identifier"] != "/docker" for endpoint in config["endpoints"]
    )


def test_configuration_for_backend_scans_endpoints(monkeypatch):
    from pycontainers.shared.runtime.config import DOCKER_ENDPOINT, PODMAN_ENDPOINT

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.resolve_docker_command_backend",
        lambda: "container",
    )
    monkeypatch.setattr(
        "pycontainers.shared.runtime.client.CONFIGURATION",
        {
            "version": "1.0",
            "name": "PyContainers",
            "server": {"type": "local"},
            "endpoints": [PODMAN_ENDPOINT, DOCKER_ENDPOINT],
        },
    )
    config = _configuration_for_backend("docker")
    docker_endpoint = next(
        endpoint for endpoint in config["endpoints"] if endpoint["identifier"] == "/docker"
    )
    assert docker_endpoint["backends"]["command"]["darwin"] == "container"


def test_pycontainers_aio_property(docker_client):
    assert isinstance(docker_client.aio, _AsyncCommandAccessor)


def test_async_accessor_getattr_dynamic_command(docker_client):
    accessor = _AsyncCommandAccessor(docker_client)
    with patch.object(
        docker_client,
        "_dispatch_command",
        new=AsyncMock(return_value="v1.0"),
    ):
        version = accessor.version
        assert asyncio.run(version()) == "v1.0"


def test_async_accessor_rejects_typed_attribute_without_method(docker_client):
    original_run = _AsyncCommandAccessor.run
    del _AsyncCommandAccessor.run
    try:
        accessor = _AsyncCommandAccessor(docker_client)
        with pytest.raises(AttributeError):
            accessor.run  # noqa: B018 — typed accessor rejects duplicate binding
    finally:
        _AsyncCommandAccessor.run = original_run


@pytest.mark.asyncio
async def test_execute_request_returns_none_when_generator_empty(docker_client):
    async def empty_session(*args, **kwargs):
        if False:
            yield  # pragma: no cover

    with patch.object(docker_client, "_session_client", side_effect=empty_session):
        assert await docker_client._execute_request(["version"]) is None


async def _async_gen(items):
    for item in items:
        yield item
