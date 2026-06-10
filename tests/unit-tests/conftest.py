import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest

from pycontainers.shared.runtime.client import PyContainers


@pytest.fixture
def docker_client() -> PyContainers:
    """Runtime client for unit tests that does not require a CLI on PATH."""
    client = PyContainers(backend="docker")
    yield client
    client._shutdown_sync()


class MockRuntimeParent:
    """Minimal parent stand-in for Container unit tests."""

    backend = "docker"

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.execute_responses: list[tuple[str, int]] = []
        self.stream_chunks: list[str] = []

    def _run_sync(self, coro):
        return self.loop.run_until_complete(coro)

    async def _execute_request(
        self,
        full_command_args: list[str],
        *,
        endpoint: str | None = None,
    ) -> tuple[str, int]:
        if self.execute_responses:
            return self.execute_responses.pop(0)
        return "ok\n[exit 0]\n", 200

    async def _stream_command(
        self,
        subcommand: str,
        full_command_args: list[str],
        *,
        endpoint: str | None = None,
    ) -> AsyncIterator[str]:
        for chunk in self.stream_chunks:
            yield chunk

    def close_loop(self) -> None:
        if not self.loop.is_closed():
            self.loop.close()


@pytest.fixture
def mock_parent() -> MockRuntimeParent:
    parent = MockRuntimeParent()
    yield parent
    parent.close_loop()
