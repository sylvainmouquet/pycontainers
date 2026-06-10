import asyncio
from unittest.mock import MagicMock, patch

import pytest

from pycontainers import CommandError, docker
from pycontainers.shared.runtime.streaming import iter_lines, sync_iterator


@pytest.mark.asyncio
async def test_iter_lines_splits_chunks():
    async def chunks():
        yield "line one\nline tw"
        yield "o\nline three"

    lines = [line async for line in iter_lines(chunks())]
    assert lines == ["line one", "line two", "line three"]


@pytest.mark.asyncio
async def test_iter_lines_handles_carriage_returns():
    async def chunks():
        yield "alpha\r\nbeta\r\n"

    lines = [line async for line in iter_lines(chunks())]
    assert lines == ["alpha", "beta"]


def test_sync_iterator_adapts_async_generator():
    async def chunks():
        yield "a"
        yield "b"

    loop = asyncio.new_event_loop()
    try:
        assert list(sync_iterator(loop, chunks())) == ["a", "b"]
    finally:
        loop.close()


@pytest.mark.asyncio
async def test_dispatch_stream_raises_on_non_zero_exit():
    async def fake_iter_request(*args, **kwargs):
        yield "failed output\n[exit 2]\n"

    with patch.object(docker, "_iter_request", side_effect=fake_iter_request):
        with pytest.raises(CommandError) as exc_info:
            async for _ in docker._dispatch_stream("logs", "demo"):
                pass

    assert exc_info.value.subcommand == "logs"
    assert exc_info.value.exit_code == 2


@pytest.mark.asyncio
async def test_dispatch_stream_yields_chunks():
    async def fake_iter_request(*args, **kwargs):
        yield "chunk-a"
        yield "chunk-b\n[exit 0]\n"

    with patch.object(docker, "_iter_request", side_effect=fake_iter_request):
        chunks = [chunk async for chunk in docker._dispatch_stream("version")]

    assert chunks == ["chunk-a", "chunk-b\n[exit 0]\n"]


@pytest.mark.asyncio
async def test_session_client_uses_stream_mode():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    async def aiter_text():
        yield "live output"

    mock_response.aiter_text = aiter_text

    class StreamContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc, tb):
            return False

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=StreamContext())

    class ClientContext:
        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with patch("pycontainers.shared.runtime.client.httpx.AsyncClient", return_value=ClientContext()):
        chunks = [
            chunk
            async for chunk in docker._iter_request(["version"], endpoint="/docker")
        ]

    assert chunks == ["live output"]
    mock_client.stream.assert_called_once()
