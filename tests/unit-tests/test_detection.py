import pytest

from pycontainers import PyContainers
from pycontainers.shared.runtime.detection import detect_runtime


def test_detect_runtime_prefers_docker(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    assert detect_runtime() == "docker"


def test_detect_runtime_falls_back_to_podman(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.shutil.which",
        lambda name: "/usr/bin/podman" if name == "podman" else None,
    )
    assert detect_runtime() == "podman"


def test_detect_runtime_raises_when_missing(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.shutil.which",
        lambda _name: None,
    )
    with pytest.raises(RuntimeError, match="No container runtime found"):
        detect_runtime()


def test_pycontainers_explicit_backend():
    docker_client = PyContainers(backend="docker")
    podman_client = PyContainers(backend="podman")

    assert docker_client.backend == "docker"
    assert docker_client._endpoint == "/docker"
    assert podman_client.backend == "podman"
    assert podman_client._endpoint == "/podman"


def test_pycontainers_auto_detects(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.shutil.which",
        lambda name: "/usr/bin/podman" if name == "podman" else None,
    )
    client = PyContainers()
    assert client.backend == "podman"


def test_pycontainers_rejects_unknown_backend():
    from pycontainers import UnsupportedBackendError

    with pytest.raises(UnsupportedBackendError, match="Unsupported backend"):
        PyContainers(backend="container")  # type: ignore[arg-type]


def test_is_runtime_available(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )

    class Result:
        returncode = 0

    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.subprocess.run",
        lambda *args, **kwargs: Result(),
    )

    from pycontainers.shared.runtime.detection import is_runtime_available

    assert is_runtime_available("docker") is True
    assert is_runtime_available("podman") is False
