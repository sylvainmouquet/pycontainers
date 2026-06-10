from pycontainers.features.podman.client import PyContainers as PodmanClient
from pycontainers.features.podman.config import CONFIGURATION, PODMAN_ENDPOINT


def test_podman_reexports():
    assert PodmanClient is not None
    assert PODMAN_ENDPOINT["identifier"] == "/podman"
    assert any(
        endpoint["identifier"] == "/podman" for endpoint in CONFIGURATION["endpoints"]
    )
