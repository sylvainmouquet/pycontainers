"""Typed kwargs for frequently used container runtime commands."""

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict


class VolumeBind(TypedDict, total=False):
    bind: str
    target: str
    mode: str


VolumeMount = str | tuple[str, str] | tuple[str, str, str] | VolumeBind
VolumeMapping = Mapping[str, VolumeMount | str | VolumeBind]
VolumeSequence = Sequence[VolumeMount | tuple[str, str] | tuple[str, str, str] | str]
PortPair = tuple[int | str, int | str]


def collect_run_kwargs(
    *,
    name: str | None = None,
    detach: bool = False,
    rm: bool = False,
    entrypoint: str | None = None,
    command: str | Sequence[str] | None = None,
    envs: Mapping[str, str] | None = None,
    volumes: VolumeMapping | VolumeSequence | None = None,
    expose: Sequence[int | str] | None = None,
    publish: Sequence[PortPair] | None = None,
    cap_add: Sequence[str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build kwargs for `docker run` / `podman run` from typed parameters."""
    kwargs: dict[str, Any] = dict(extra or {})
    if name is not None:
        kwargs["name"] = name
    if detach:
        kwargs["detach"] = True
    if rm:
        kwargs["rm"] = True
    if entrypoint is not None:
        kwargs["entrypoint"] = entrypoint
    if command is not None:
        kwargs["command"] = command
    if envs is not None:
        kwargs["envs"] = envs
    if volumes is not None:
        kwargs["volumes"] = volumes
    if expose is not None:
        kwargs["expose"] = expose
    if publish is not None:
        kwargs["publish"] = publish
    if cap_add is not None:
        kwargs["cap_add"] = cap_add
    return kwargs


def collect_ps_kwargs(
    *,
    all: bool = False,
    filter: Mapping[str, str] | None = None,
    filters: Mapping[str, str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build kwargs for `docker ps` / `podman ps` from typed parameters."""
    kwargs: dict[str, Any] = dict(extra or {})
    if all:
        kwargs["all"] = True
    if filter is not None:
        kwargs["filter"] = filter
    if filters is not None:
        kwargs["filters"] = filters
    return kwargs


def collect_pull_kwargs(
    *,
    command: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build kwargs for `docker pull` / `podman pull` from typed parameters."""
    kwargs: dict[str, Any] = dict(extra or {})
    if command is not None:
        kwargs["command"] = command
    return kwargs
