# Architecture

PyContainers sits between application code and the container runtime CLI.

## System overview

```text
Application (sync or asyncio)
        │
        ▼
  PyContainers client          ← dynamic command dispatch, backend selection
        │
        ▼
  ProxyCraft (ASGI app)        ← routes /docker/** and /podman/** to CLI backends
        │
        ▼
  docker | podman | container  ← platform-specific binary
```

## Major components

| Component | Location | Role |
|-----------|----------|------|
| Public API | `pycontainers/__init__.py` | Exports `docker`, `podman`, `PyContainers`, `Container`, `ComposeClient`, `ComposeService`, `detect_runtime` |
| Runtime core | `pycontainers/shared/runtime/` | Shared client, container model, ProxyCraft config, runtime detection |
| Docker feature | `pycontainers/features/docker/` | Docker-specific re-exports |
| Podman feature | `pycontainers/features/podman/` | Podman-specific re-exports |
| Compose feature | `pycontainers/features/compose/` | Multi-container project lifecycle and service accessors |
| Shared utilities | `pycontainers/shared/` | CLI builder, logging, result parsing, typed command kwargs |
| Error types | `pycontainers/shared/errors.py` | `CommandError`, `UnsupportedBackendError`, and base `PyContainersError` |
| Tests | `tests/unit-tests/`, `tests/backends/` | Unit tests and per-backend integration tests (docker, container, podman) |

## Continuous integration

GitHub Actions (`.github/workflows/test.yml`) runs four jobs:

| Job | Runner | Scope |
|-----|--------|-------|
| `unit tests` | `ubuntu-latest` | Pyright and `tests/unit-tests/` |
| `docker` | `ubuntu-latest` | `tests/backends/docker/` via `just test-docker` |
| `podman` | `ubuntu-latest` | `tests/backends/podman/` via `just test-podman` (Podman installed in CI) |
| `container` | `macos-latest` | `tests/backends/container/` via `just test-container` |

Shared setup steps live in `.github/actions/setup/`. The composite test action (`.github/actions/test/`) runs unit tests and type checking only; each backend has its own workflow job so results are visible separately in GitHub Actions.

## Runtime selection

Callers can choose a backend in three ways:

1. **Explicit singleton** — `from pycontainers import docker` or `podman`
2. **Constructor argument** — `PyContainers(backend="podman")`
3. **Auto-detection** — `PyContainers()` or `detect_runtime()` picks `docker` when both CLIs are on `PATH`, otherwise `podman`

ProxyCraft endpoint configuration lives in `pycontainers/shared/runtime/config.py`. Each endpoint maps platform keys (`darwin`, `linux`, `default`) to the CLI binary name.

On macOS, the docker endpoint resolves at runtime: Colima, Docker Desktop, or any responsive `docker` CLI is preferred; Apple's `container` CLI is used only when `docker` is unavailable.

## Dependencies

- **ProxyCraft** — proxies HTTP requests to local CLI processes
- **httpx** — ASGI transport for in-process ProxyCraft calls
- **nest-asyncio** — allows nested event loops when invoked from async contexts

## Design decisions

- Prefer CLI compatibility over reimplementing the Docker/Podman API; any subcommand the CLI supports can be called dynamically.
- Keep feature code inside `features/` and only promote code to `shared/` when multiple features need it.
- Use ProxyCraft configuration to map platforms to the correct binary per endpoint.
