from pycontainers.features.docker.config import DOCKER_ENDPOINT
from pycontainers.shared.runtime.config import CONFIGURATION


def test_docker_endpoint_uses_container_on_darwin():
    command_backend = DOCKER_ENDPOINT["backends"]["command"]
    assert command_backend["darwin"] == "container"
    assert command_backend["default"] == "docker"


def test_configuration_includes_docker_endpoint():
    docker_endpoints = [
        endpoint
        for endpoint in CONFIGURATION["endpoints"]
        if endpoint["identifier"] == "/docker"
    ]
    assert len(docker_endpoints) == 1
    assert docker_endpoints[0]["backends"]["command"]["darwin"] == "container"
