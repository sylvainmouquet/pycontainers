# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

- Typed `run`, `ps`, and `pull` wrappers on `PyContainers` and `docker.aio` with explicit kwargs for common options
- `CommandError`, `UnsupportedBackendError`, and `PyContainersError` for structured CLI failure handling
- Pyright configuration and CI gate via `just check`
- Compose and stack operations via `docker.compose` with project lifecycle helpers and `ComposeService` accessors
- Compose usage example at `examples/docker/example_docker_compose.py`
- Native async API via `docker.aio` and `container.aio` for coroutine-friendly CLI dispatch
- Async usage example at `examples/docker/example_docker_async.py`
- Podman backend with a dedicated ProxyCraft `/podman` endpoint
- `podman` singleton and `detect_runtime()` for explicit or automatic runtime selection
- Shared runtime module (`pycontainers/shared/runtime/`) for Docker and Podman clients
- Integration tests for Podman (skipped when the CLI is unavailable)

### Changed

- Non-zero CLI exit codes now raise `CommandError` instead of a bare `ValueError`
- `PyContainers` accepts an optional `backend` argument (`"docker"` or `"podman"`)
- ProxyCraft configuration moved to `pycontainers/shared/runtime/config.py`

### Fixed

### Removed
