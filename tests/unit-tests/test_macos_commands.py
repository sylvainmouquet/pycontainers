import json
import sys
from unittest.mock import patch

import pytest

from pycontainers.shared.runtime.macos_commands import (
    adapt_command_line_for_macos,
    is_macos_container_available,
    normalize_macos_list_entry,
    parse_macos_container_list,
    uses_macos_container_cli,
)


def test_uses_macos_container_cli_false_for_podman():
    assert uses_macos_container_cli("podman") is False


def test_uses_macos_container_cli_true_when_container_backend(monkeypatch):
    monkeypatch.setattr(
        "pycontainers.shared.runtime.detection.resolve_docker_command_backend",
        lambda: "container",
    )
    assert uses_macos_container_cli("docker") is True


def test_adapt_command_line_empty():
    assert adapt_command_line_for_macos([]) == []


def test_adapt_command_line_pull_prefix():
    adapted = adapt_command_line_for_macos(["pull", "alpine"])
    assert adapted == ["images", "pull", "alpine"]


def test_adapt_command_line_skips_filter_flag():
    adapted = adapt_command_line_for_macos(["ps", "--filter", "name=web", "--no-trunc"])
    assert adapted == ["list"]


def test_adapt_command_line_passthrough_for_unknown_command():
    adapted = adapt_command_line_for_macos(["run", "alpine"])
    assert adapted == ["run", "alpine"]
    adapted = adapt_command_line_for_macos(["ps", "--format=json"])
    assert adapted == ["list", "--format", "json"]


def test_adapt_command_line_format_equals():
    adapted = adapt_command_line_for_macos(["ps", "--format=json"])
    assert adapted == ["list", "--format", "json"]


def test_normalize_macos_list_entry_with_dict_image():
    item = {
        "configuration": {"id": "abc", "image": {"reference": "alpine:3.20"}},
        "status": "running",
    }
    assert normalize_macos_list_entry(item) == {
        "ID": "abc",
        "Image": "alpine:3.20",
        "Status": "running",
        "Names": "abc",
    }


def test_normalize_macos_list_entry_with_string_image():
    item = {"configuration": {"id": "abc", "image": "alpine"}, "status": "stopped"}
    normalized = normalize_macos_list_entry(item)
    assert normalized["Image"] == "alpine"


def test_normalize_macos_list_entry_without_configuration():
    item = {"status": "running"}
    normalized = normalize_macos_list_entry(item)
    assert normalized["ID"] == ""
    assert normalized["Image"] == ""


def test_parse_macos_container_list_empty():
    assert parse_macos_container_list("") == []


def test_parse_macos_container_list_single_dict():
    payload = json.dumps({"configuration": {"id": "abc"}, "status": "running"})
    rows = parse_macos_container_list(payload)
    assert len(rows) == 1
    assert rows[0]["ID"] == "abc"


def test_parse_macos_container_list_array():
    payload = json.dumps([{"configuration": {"id": "one"}, "status": "running"}])
    assert len(parse_macos_container_list(payload)) == 1


def test_parse_macos_container_list_invalid_type():
    assert parse_macos_container_list(json.dumps("not-a-container")) == []


def test_is_macos_container_available_false_off_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert is_macos_container_available() is False


def test_is_macos_container_available_false_without_binary(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.macos_commands.shutil.which",
        lambda _name: None,
    )
    assert is_macos_container_available() is False


def test_is_macos_container_available_true(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        "pycontainers.shared.runtime.macos_commands.shutil.which",
        lambda name: "/usr/local/bin/container" if name == "container" else None,
    )

    class Result:
        returncode = 0

    monkeypatch.setattr(
        "pycontainers.shared.runtime.macos_commands.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    assert is_macos_container_available() is True
