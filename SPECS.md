# PyContainers — Product Specification

PyContainers is a Python wrapper for communicating with the Docker, macOS Container, and Podman CLIs. It offers a lightweight alternative to docker-py and python-on-whales by proxying CLI commands through ProxyCraft and exposing a dynamic, Pythonic API.

## High impact, relatively simple

### 1. Docker CLI wrapper

**Status:** Done

Dynamic dispatch for any Docker subcommand via attribute access on a shared `docker` client instance. Commands such as `pull`, `ps`, `run`, and `rm` are invoked without hand-written wrappers for each subcommand.

- [x] Dynamic `__getattr__` command dispatch on `PyContainers`
- [x] JSON-formatted `ps` output parsed into `Container` objects
- [x] `run` returns a `Container` with loaded environment configuration
- [x] Non-zero CLI exit codes surfaced as `ValueError`
- [x] Works inside and outside an active asyncio event loop

**Key files:** `pycontainers/features/docker/client.py`, `pycontainers/features/docker/__init__.py`, `pycontainers/__init__.py`

---

### 2. Container model

**Status:** Done

Rich container objects returned by `docker.ps()` and `docker.run()`, with instance-level command execution and environment access.

- [x] Attribute-based access to inspect/ps fields
- [x] `execute` alias for `docker exec` on a container instance
- [x] `ContainerEnv` dict-like mapping with `KEY=VALUE` iteration
- [x] Environment loaded from inspect, exec fallback, or runtime `envs` kwargs

**Key files:** `pycontainers/features/docker/container.py`

---

### 3. Command-line argument builder

**Status:** Done

Translates Python kwargs into Docker CLI flags and positional arguments, covering common `run` and `ps` options.

- [x] Filter and boolean flag handling
- [x] Volume mounts (list and dict forms)
- [x] Port publishing and expose
- [x] Environment variables (`envs`)
- [x] Capability adds (`cap_add`)
- [x] Entrypoint and command splitting

**Key files:** `pycontainers/shared/utilities/command_line.py`

---

### 4. Shared logging

**Status:** Done

Centralized logging helpers used across features, with a null handler on the package logger to avoid polluting application output.

- [x] Feature-scoped loggers via `get_logger`
- [x] Package-level `NullHandler` registration

**Key files:** `pycontainers/shared/logging/logger.py`, `pycontainers/__init__.py`

---

## Medium impact — broadens scope

### 5. Feature-based package layout

**Status:** Done

Code organized by capability (`features/docker`) with reusable infrastructure in `shared/`, replacing the flat `pycontainer` package.

- [x] `pycontainers/features/docker/` for Docker-specific logic
- [x] `pycontainers/shared/` for cross-feature utilities and logging
- [x] Package rename from `pycontainer` to `pycontainers`
- [x] Just-based task runner replacing Makefile

**Key files:** `pycontainers/features/docker/`, `pycontainers/shared/`, `justfile`, `pyproject.toml`

---

### 6. Podman backend

**Status:** Done

Support Podman as a first-class runtime alongside Docker, selectable per platform or explicitly by the caller.

- [x] Podman backend configuration in ProxyCraft endpoints
- [x] Runtime auto-detection or explicit backend selection
- [x] Integration tests against Podman

**Key files:** `pycontainers/shared/runtime/`, `pycontainers/features/podman/`, `pycontainers/__init__.py`

---

### 7. macOS Container CLI backend

**Status:** Done

Support Apple's `container` CLI on macOS as described in the project README.

- [x] macOS-specific backend mapping in ProxyCraft config
- [x] Smoke tests on macOS runners

**Key files:** `pycontainers/shared/runtime/config.py`, `pycontainers/shared/runtime/macos_commands.py`, `pycontainers/features/docker/config.py`, `tests/smoke/test_macos_container.py`

---

### 8. Compose and stack operations

**Status:** Done

Higher-level workflows for multi-container applications via `docker compose` (or equivalent) subcommands.

- [x] Compose project lifecycle helpers (`up`, `down`, `ps`, and dynamic subcommand dispatch)
- [x] Service-level accessors (`ComposeService` with `exec`, `logs`, and async variants)
- [x] Project scoping via `docker.compose(file=..., project_name=...)`
- [x] Async compose commands via `compose.aio` and `service.aio`

**Key files:** `pycontainers/features/compose/`, `pycontainers/shared/runtime/client.py`, `examples/docker/example_docker_compose.py`

---

## Polish & UX

### 9. Native async API

**Status:** Done

Expose async-first methods instead of wrapping every call with `asyncio.run` inside synchronous handlers.

- [x] Async variants for `PyContainers` commands via `docker.aio`
- [x] Async container execution helpers via `container.aio`
- [x] Documented asyncio usage patterns in `README.md` and `examples/docker/example_docker_async.py`

**Key files:** `pycontainers/shared/runtime/client.py`, `pycontainers/shared/runtime/container.py`, `examples/docker/example_docker_async.py`

---

### 10. Type safety and developer experience

**Status:** Done

Improve static analysis, IDE autocomplete, and error messages for common Docker kwargs.

- [x] Typed wrappers for frequently used commands (`run`, `ps`, `pull`)
- [x] Pyright clean CI gate (`just check`)
- [x] Richer error types beyond generic `ValueError`

**Key files:** `pycontainers/shared/runtime/client.py`, `pycontainers/shared/runtime/types.py`, `pycontainers/shared/errors.py`, `pyrightconfig.json`, `justfile`

---

### 11. Documentation and examples

**Status:** Planned

Long-form docs, feature READMEs, and kept-up-to-date examples aligned with the feature-based layout.

- [ ] `docs/architecture.md` with system overview and data flow
- [ ] Feature README for Docker
- [ ] Expanded examples beyond `examples/docker/example_docker.py`

**Potential files:** `docs/architecture.md`, `examples/docker/example_docker.py`, `README.md`

---

## New Opportunities

### 12. CI coverage enforcement

**Status:** Done

Automated coverage collection and threshold enforcement in GitHub Actions, with results visible on pull requests.

- [x] pytest-cov integration in CI
- [x] Coverage summary in GitHub Actions
- [x] PR coverage comments or badge

**Key files:** `.github/actions/test/action.yml`, `.github/workflows/test.yml`, `justfile`, `pyproject.toml`, `docs/decisions/0003-ci-coverage-policy.md`

---

### 13. Streaming command output

**Status:** Done

Stream stdout/stderr from long-running or verbose Docker commands instead of buffering full responses.

- [x] Stream mode in `_session_client`
- [x] Iterator-based API for log following

**Key files:** `pycontainers/shared/runtime/client.py`, `pycontainers/shared/runtime/container.py`, `pycontainers/shared/runtime/streaming.py`

---

## Recommended Roadmap

1. **Stabilize the refactor** — finish the `pycontainer` → `pycontainers` migration, update CI workflows, and publish a release.
2. **Document the architecture** — ship `docs/architecture.md` and link it from `README.md`.
3. **Expand runtime support** — add Podman and macOS Container backends.
4. **Improve the developer experience** — typed command helpers, native async API, and clearer errors.
5. **Broaden scope** — compose support and streaming output for operational workflows.

---

## Architecture notes

PyContainers sits between application code and the container runtime CLI:

```text
Application (sync or asyncio)
        │
        ▼
  PyContainers client          ← dynamic command dispatch
        │
        ▼
  ProxyCraft (ASGI app)        ← routes /docker/** and /podman/** to CLI backends
        │
        ▼
  docker | podman | container  ← platform-specific binary
```

**Major components**

| Component | Location | Role |
|-----------|----------|------|
| Public API | `pycontainers/__init__.py` | Exports `docker` and `podman` singletons, `PyContainers`, `Container`, `ComposeClient`, `ComposeService`, `detect_runtime` |
| Runtime core | `pycontainers/shared/runtime/` | Shared client, container model, ProxyCraft config, runtime detection |
| Docker feature | `pycontainers/features/docker/` | Docker-specific re-exports |
| Podman feature | `pycontainers/features/podman/` | Podman-specific re-exports |
| Compose feature | `pycontainers/features/compose/` | Multi-container project lifecycle and service accessors |
| Shared utilities | `pycontainers/shared/` | CLI builder, logging, result parsing |
| Tests | `tests/unit-tests/` | Unit and integration tests against a live Docker daemon |

**Dependencies**

- **ProxyCraft** — proxies HTTP requests to local CLI processes
- **httpx** — ASGI transport for in-process ProxyCraft calls
- **nest-asyncio** — allows nested event loops when invoked from async contexts

**Design decisions**

- Prefer CLI compatibility over reimplementing the Docker API; any subcommand the CLI supports can be called dynamically.
- Keep feature code inside `features/` and only promote code to `shared/` when multiple features need it.
- Use ProxyCraft configuration (`pycontainers/shared/runtime/config.py`) to map platforms to the correct binary.
- Expose explicit runtime clients via `docker` and `podman` singletons; `PyContainers()` auto-detects the first available CLI on `PATH`.
