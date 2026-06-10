import asyncio

from pycontainers import docker


async def main():
    await docker.aio.pull("ubuntu:20.04")

    containers = await docker.aio.ps(all=True)
    for container in containers:
        print(container)

    container = await docker.aio.run(
        "ubuntu:20.04",
        detach=True,
        entrypoint="/bin/echo",
        command=["hello from async pycontainers"],
    )
    print(await container.aio.execute("echo done"))
    await container.aio.rm()


if __name__ == "__main__":
    asyncio.run(main())
