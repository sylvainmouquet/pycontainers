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
from pycontainers import docker

if __name__ == "__main__":
    containers = docker.ps(all=False)
    for container in containers:
        print(container)
```

## Documentation

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