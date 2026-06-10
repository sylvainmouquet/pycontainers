# Development

This project uses [Just](https://github.com/casey/just) as its task runner. The `justfile` at the repository root is the single source of truth for build, test, lint, and release commands.

Install Just with `brew install just` or see the [installation guide](https://github.com/casey/just#installation).

## Setup

Clone [proxycraft](https://github.com/sylvainmouquet/proxycraft) as a sibling of this repository so `../proxycraft` resolves:

```text
workspace/
├── pycontainers/
└── proxycraft/
```

Then install dependencies:

```bash
just install
```

CI clones proxycraft automatically when the sibling checkout is not present.

## Common tasks

```bash
just --list                              # List available recipes
just test                                # Run all tests
just test-cov                            # Run unit tests with coverage enforcement
just test tests/unit-tests/test_model.py # Run specific tests
just test-docker                         # Docker backend integration tests
just test-container                      # Apple container backend tests (macOS)
just test-podman                         # Podman backend integration tests
just lint                                # Lint and verify formatting
just format                              # Apply code formatting
just check                               # Run pyright type checker
just example-docker                      # Smoke-test the Docker usage example
just update                              # Upgrade and sync dependencies
just check-deps                          # List outdated dependencies
```

## Build and release

The build recipe requires a `VERSION` environment variable:

```bash
VERSION=2.0.0 just build
just install-local                       # Install the local wheel
just deploy                              # Upload to PyPI
```

## CI alignment

GitHub Actions workflows invoke the same `just` recipes used locally (`.github/actions/setup/`, `.github/actions/test/`, and `.github/workflows/test.yml`). When adding a new development task, add a recipe to `justfile` first, then call it from CI.

The unit-test job runs `just test-cov`, which collects line coverage for the `pycontainers` package via `coverage run`, enforces a **100%** minimum threshold (`COVERAGE_FAIL_UNDER`, default 100), writes `coverage.xml`, and publishes a summary in the job output. Pull requests receive an automated coverage comment. See [ADR 0003](../decisions/0003-ci-coverage-policy.md) for policy details.
