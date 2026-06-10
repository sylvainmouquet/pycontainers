<h1 align="center">
PyContainers
</h1>

<p align="center"><i>pycontainers is a wrapper to communicate with the docker/container(MacOs)/podman cli.</i>
Alternative to docker-py and python-on-whales</p>

## 🚀 Quick Start

## Installation

```bash
pip install pycontainers
```

Or with uv:

```bash
uv add pycontainers
```

### Basic Usage

```python
from pycontainers import docker, podman

if __name__ == "__main__":
    containers = docker.ps(all=False)
    for container in containers:
        print(container)

    # Or use Podman explicitly
    podman_containers = podman.ps(all=False)
```

You can also auto-detect the first available runtime (`docker`, then `podman`):

```python
from pycontainers import PyContainers

runtime = PyContainers()
print(runtime.backend)
```

### Async Usage

Use the `aio` namespace inside coroutines to avoid nested `asyncio.run` calls:

```python
import asyncio

from pycontainers import docker


async def main():
    await docker.aio.pull("ubuntu:20.04")
    containers = await docker.aio.ps(all=False)
    for container in containers:
        print(container)

    container = await docker.aio.run(
        "alpine",
        detach=True,
        entrypoint="/bin/sh",
        command=["-c", "sleep 60"],
    )
    output = await container.aio.execute("echo hello")
    print(output)
    await container.aio.rm()


if __name__ == "__main__":
    asyncio.run(main())
```

Synchronous callers can keep using `docker.ps()`, `docker.run()`, and `container.execute()` as before. These commands expose typed kwargs for common options (`name`, `detach`, `envs`, `volumes`, `filter`, and more).

Failed CLI commands raise `CommandError` with `subcommand`, `exit_code`, and `output` attributes:

```python
from pycontainers import CommandError, docker

try:
    docker.run("bad-image")
except CommandError as error:
    print(error.subcommand, error.exit_code, error.output)
```

### Compose Usage

Manage multi-container projects through `docker.compose` (or `podman.compose`):

```python
from pycontainers import docker

project = docker.compose(file="docker-compose.yml", project_name="demo")
project.up(detach=True, build=True)

for service in project.ps():
    print(service)

web = project.service("web")
print(web.exec("echo hello from compose"))

project.down(volumes=True)
```

## Documentation

- [Product specification](SPECS.md)
- [Architecture](docs/architecture.md)

## Development

This project uses [Just](https://github.com/casey/just) as its task runner. Install it with `brew install just` or see the [installation guide](https://github.com/casey/just#installation).

```bash
just --list                              # List available commands
just install                             # Install dependencies
just test                                # Run all tests
just test tests/unit-tests/test_model.py  # Run specific tests
just lint                                # Run linter and formatter
just check                               # Run pyright type checker
just update                              # Update dependencies
just check-deps                          # Check for outdated dependencies
VERSION=1.0.0 just build                 # Build the package (VERSION is required)
just install-local                       # Install the local wheel build
just deploy                              # Deploy to PyPI
```

## 📄 License

[MIT](LICENSE)