<h1 align="center">
PyContainer
</h1>

<p align="center"><i>pycontainer is a wrapper to communicate with the docker/container(MacOs)/podman cli.</i>
Alternative to docker-py and python-on-whales</p>

## 🚀 Quick Start

## Installation

```bash
pip install pycontainer
```

Or with uv:

```bash
uv add pycontainer
```

### Basic Usage

```python
from pycontainer import docker

if __name__ == "__main__":
    containers = docker.ps(all=False)
    for container in containers:
        print(container)
```



## 📄 License

[MIT](LICENSE)