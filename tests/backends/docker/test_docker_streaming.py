import uuid

import pytest

from pycontainers import docker

from tests.backends.markers import requires_docker

pytestmark = requires_docker


@pytest.mark.asyncio
async def test_async_stream_version():
    chunks: list[str] = []
    async for chunk in docker.aio.stream("version"):
        chunks.append(chunk)

    output = "".join(chunks)
    assert output
    assert "Version" in output or "version" in output.lower()


@pytest.mark.asyncio
async def test_sync_stream_version():
    chunks = list(docker.stream("version"))
    output = "".join(chunks)
    assert output
    assert "Version" in output or "version" in output.lower()


@pytest.mark.asyncio
async def test_async_container_log_lines():
    name = uuid.uuid4()
    container = await docker.aio.run(
        "alpine",
        name=name,
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "echo streamed-log-line"],
    )

    lines = [line async for line in container.aio.stream_lines("logs")]
    assert any("streamed-log-line" in line for line in lines)

    await container.aio.rm(force=True)
