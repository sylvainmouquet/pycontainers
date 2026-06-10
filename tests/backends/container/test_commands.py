import sys

from pycontainers.shared.runtime.macos_commands import (
    adapt_command_line_for_macos,
    normalize_macos_list_entry,
    parse_macos_container_list,
    uses_macos_container_cli,
)


def test_uses_macos_container_cli_on_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.is_runtime_available",
        lambda _backend: False,
    )
    monkeypatch.setattr(
        "pycontainers.shared.runtime.macos_commands.is_macos_container_available",
        lambda: True,
    )
    assert uses_macos_container_cli("docker") is True
    assert uses_macos_container_cli("podman") is False


def test_uses_macos_container_cli_false_when_docker_available_on_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.is_runtime_available",
        lambda backend: backend == "docker",
    )
    assert uses_macos_container_cli("docker") is False


def test_uses_macos_container_cli_off_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert uses_macos_container_cli("docker") is False


def test_adapt_ps_to_list():
    assert adapt_command_line_for_macos(["ps", "--format=json", "--no-trunc"]) == [
        "list",
        "--format",
        "json",
    ]


def test_adapt_ps_with_all_flag():
    assert adapt_command_line_for_macos(
        ["ps", "--format=json", "--no-trunc", "--all"]
    ) == ["list", "--format", "json", "--all"]


def test_adapt_pull_to_images_pull():
    assert adapt_command_line_for_macos(["pull", "ubuntu:20.04"]) == [
        "images",
        "pull",
        "ubuntu:20.04",
    ]


def test_adapt_removes_unsupported_filter_flag():
    assert adapt_command_line_for_macos(
        ["ps", "--format=json", "--no-trunc", "--filter", "name=^foo"]
    ) == ["list", "--format", "json"]


def test_normalize_macos_list_entry():
    item = {
        "status": "running",
        "configuration": {
            "id": "abc123",
            "image": {"reference": "alpine:latest"},
        },
    }
    assert normalize_macos_list_entry(item) == {
        "ID": "abc123",
        "Image": "alpine:latest",
        "Status": "running",
        "Names": "abc123",
    }


def test_parse_macos_container_list_array():
    payload = """[
        {
            "status": "running",
            "configuration": {
                "id": "abc123",
                "image": {"reference": "alpine:latest"}
            }
        }
    ]"""
    rows = parse_macos_container_list(payload)
    assert rows == [
        {
            "ID": "abc123",
            "Image": "alpine:latest",
            "Status": "running",
            "Names": "abc123",
        }
    ]


def test_parse_macos_container_list_empty():
    assert parse_macos_container_list("") == []
    assert parse_macos_container_list("[]") == []
