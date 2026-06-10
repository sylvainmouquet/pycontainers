import asyncio

from pycontainers import docker


async def main():
    output = docker.run(command="hello-world", volumes=["/tmp", "/var/tmp"])
    print(output)

    print(docker.pull("ubuntu:20.04"))  # Predefined method
    # docker.run("ubuntu", interactive=True)  # Predefined with options
    docker.ps(all=True)  # Dynamic method
    # print(my_docker_image.repo_tags)

    # Predefined methods work as expected
    result1 = docker.pull("ubuntu:20.04")
    print(f"Result: {result1}")

    result2 = docker.run("ubuntu:20.04", "bash", rm=True)
    print(f"Result: {result2}")

    # Dynamic methods work too!
    result3 = docker.ps(all=True)
    print(f"Result: {result3}")


if __name__ == "__main__":
    asyncio.run(main())
