import asyncio
from collections.abc import AsyncIterator, Iterator


async def iter_lines(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Yield complete lines from an async stream of text chunks."""
    pending = ""
    async for chunk in chunks:
        pending += chunk
        while "\n" in pending:
            line, pending = pending.split("\n", 1)
            yield line.rstrip("\r")

    if pending:
        for line in pending.splitlines():
            yield line.rstrip("\r")


def sync_iterator(
    loop: asyncio.AbstractEventLoop, async_iter: AsyncIterator[str]
) -> Iterator[str]:
    """Adapt an async text iterator to a blocking sync iterator."""
    while True:
        try:
            yield loop.run_until_complete(async_iter.__anext__())
        except StopAsyncIteration:
            break
