import pytest

from pycontainers.features.compose.detection import (
    is_compose_available,
    resolve_compose_endpoint,
    resolve_compose_invocation,
)


def test_resolve_compose_invocation_prefers_plugin(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection._compose_plugin_available",
        lambda _backend: True,
    )
    monkeypatch.setattr(
        "pycontainers.features.compose.detection._standalone_compose_binary",
        lambda _backend: "docker-compose",
    )
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.uses_macos_container_cli",
        lambda _backend: False,
    )

    assert resolve_compose_invocation("docker") == "plugin"


def test_resolve_compose_invocation_falls_back_to_standalone(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection._compose_plugin_available",
        lambda _backend: False,
    )
    monkeypatch.setattr(
        "pycontainers.features.compose.detection._standalone_compose_binary",
        lambda _backend: "docker-compose",
    )
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.uses_macos_container_cli",
        lambda _backend: False,
    )

    assert resolve_compose_invocation("docker") == "standalone"


def test_resolve_compose_invocation_unavailable_on_macos_container(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.uses_macos_container_cli",
        lambda _backend: True,
    )

    assert resolve_compose_invocation("docker") is None
    assert is_compose_available("docker") is False


def test_resolve_compose_endpoint():
    assert resolve_compose_endpoint("docker", "plugin") == "/docker"
    assert resolve_compose_endpoint("docker", "standalone") == "/docker-compose"
    assert resolve_compose_endpoint("podman", "standalone") == "/podman-compose"


def test_is_compose_available_when_standalone_exists(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.resolve_compose_invocation",
        lambda _backend: "standalone",
    )

    assert is_compose_available("docker") is True


def test_is_compose_available_when_missing(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.resolve_compose_invocation",
        lambda _backend: None,
    )

    assert is_compose_available("docker") is False


def test_compose_plugin_available_false_when_binary_missing(monkeypatch):
    from pycontainers.features.compose.detection import _compose_plugin_available

    monkeypatch.setattr(
        "pycontainers.features.compose.detection.shutil.which",
        lambda _name: None,
    )
    assert _compose_plugin_available("docker") is False


def test_compose_plugin_available_true_when_version_succeeds(monkeypatch):
    from pycontainers.features.compose.detection import _compose_plugin_available

    monkeypatch.setattr(
        "pycontainers.features.compose.detection.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )

    class Result:
        returncode = 0

    monkeypatch.setattr(
        "pycontainers.features.compose.detection.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    assert _compose_plugin_available("docker") is True


def test_standalone_compose_binary_missing(monkeypatch):
    from pycontainers.features.compose.detection import _standalone_compose_binary

    monkeypatch.setattr(
        "pycontainers.features.compose.detection.shutil.which",
        lambda _name: None,
    )
    assert _standalone_compose_binary("docker") is None


def test_standalone_compose_binary_invalid_version(monkeypatch):
    from pycontainers.features.compose.detection import _standalone_compose_binary

    monkeypatch.setattr(
        "pycontainers.features.compose.detection.shutil.which",
        lambda name: "docker-compose" if name == "docker-compose" else None,
    )

    class Result:
        returncode = 1

    monkeypatch.setattr(
        "pycontainers.features.compose.detection.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    assert _standalone_compose_binary("docker") is None


def test_resolve_compose_invocation_logs_warning_when_unavailable(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        "pycontainers.features.compose.detection.uses_macos_container_cli",
        lambda _backend: False,
    )
    monkeypatch.setattr(
        "pycontainers.features.compose.detection._compose_plugin_available",
        lambda _backend: False,
    )
    monkeypatch.setattr(
        "pycontainers.features.compose.detection._standalone_compose_binary",
        lambda _backend: None,
    )

    assert resolve_compose_invocation("docker") is None
    captured = capsys.readouterr().out
    assert "Compose is unavailable" in captured
