# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added

### Changed

- Minimum supported Python version raised to 3.14
- ProxyCraft dependency uses editable local path (`../proxycraft`) for development; CI clones the repository alongside the workspace when the checkout is missing

### Fixed

- Docker backend on Linux: set explicit `linux` command in ProxyCraft config so proxycraft does not resolve a `None` platform override instead of `default`
- Sync runtime calls from async contexts (for example pytest-asyncio backend tests) no longer fail with `sniffio.AsyncLibraryNotFoundError` on Python 3.14

### Removed

- `nest-asyncio` dependency; sync dispatch now uses a dedicated background event loop instead

## [2.0.0] - 2026-06-10

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
- Streaming command output via `stream`, `stream_lines`, and `follow_logs` on `PyContainers`, `docker.aio`, and `Container`
- Development guide at `docs/development.md` and ADR for Just-based task runner
- Structured logging across runtime dispatch, compose, container commands, and runtime detection
- CI coverage collection and enforcement via `just test-cov` with GitHub Actions summaries and pull request comments
- Comprehensive unit tests for runtime client, container, compose, macOS command adaptation, logging, and utilities (218 tests, 100% line coverage)

### Changed

- ProxyCraft import updated to `proxycraft.features.configuration.models` for ProxyCraft 2 feature-based layout
- CI coverage threshold raised to **100%** line coverage; `just test-cov` now uses `coverage run` for accurate measurement
- Non-zero CLI exit codes now raise `CommandError` instead of a bare `ValueError`
- `PyContainers` accepts an optional `backend` argument (`"docker"` or `"podman"`)
- ProxyCraft configuration moved to `pycontainers/shared/runtime/config.py`
- Runtime cleanup failures are logged with `logger.warning` instead of `print()`

### Fixed

### Removed
