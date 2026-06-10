"""Map Docker-compatible subcommands to Apple container CLI equivalents on macOS."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any

MACOS_COMMAND_ALIASES: dict[str, str] = {
    "ps": "list",
}

MACOS_PREFIXED_COMMANDS: dict[str, tuple[str, ...]] = {
    "pull": ("images", "pull"),
}

MACOS_UNSUPPORTED_FLAGS = frozenset({"--no-trunc"})


def uses_macos_container_cli(backend: str) -> bool:
    """Return True when the docker backend should invoke Apple's container CLI."""
    return backend == "docker" and sys.platform == "darwin"


def adapt_command_line_for_macos(cmd_parts: list[str]) -> list[str]:
    """Translate Docker-style argv into Apple container CLI argv."""
    if not cmd_parts:
        return cmd_parts

    adapted = list(cmd_parts)
    command = adapted[0]

    if command in MACOS_PREFIXED_COMMANDS:
        adapted = [*MACOS_PREFIXED_COMMANDS[command], *adapted[1:]]
    elif command in MACOS_COMMAND_ALIASES:
        adapted[0] = MACOS_COMMAND_ALIASES[command]

    normalized: list[str] = [adapted[0]]
    index = 1
    while index < len(adapted):
        part = adapted[index]
        if part in MACOS_UNSUPPORTED_FLAGS:
            index += 1
            continue
        if part == "--filter":
            index += 2
            continue
        if part.startswith("--format="):
            normalized.extend(["--format", part.split("=", 1)[1]])
            index += 1
            continue
        normalized.append(part)
        index += 1

    return normalized


def normalize_macos_list_entry(item: dict[str, Any]) -> dict[str, str]:
    """Map Apple container list JSON into docker.ps()-compatible fields."""
    configuration = item.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}

    image = configuration.get("image")
    image_ref = ""
    if isinstance(image, dict):
        image_ref = str(image.get("reference", ""))
    elif image is not None:
        image_ref = str(image)

    container_id = str(configuration.get("id", ""))
    status = item.get("status", "")

    return {
        "ID": container_id,
        "Image": image_ref,
        "Status": str(status),
        "Names": container_id,
    }


def parse_macos_container_list(result: str) -> list[dict[str, str]]:
    """Parse `container list --format json` output into flat container dicts."""
    cleaned = result.strip()
    if not cleaned:
        return []

    parsed = json.loads(cleaned)
    if isinstance(parsed, dict):
        items = [parsed]
    elif isinstance(parsed, list):
        items = parsed
    else:
        return []

    return [
        normalize_macos_list_entry(item) for item in items if isinstance(item, dict)
    ]


def is_macos_container_available() -> bool:
    """Return True when Apple's container CLI is installed and responsive."""
    if sys.platform != "darwin":
        return False
    if shutil.which("container") is None:
        return False

    result = subprocess.run(
        ["container", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
