# ADR 0003: CI coverage policy

## Status

Accepted

## Context

The project targets 100% test coverage for production code. CI must collect coverage on every run, surface results on pull requests, and prevent regressions without blocking unrelated work while coverage is still ramping up.

## Decision

1. **Tooling:** Use `pytest-cov` with configuration in `pyproject.toml`.
2. **Local and CI entry point:** `just test-cov` runs unit tests under `tests/unit-tests/` with coverage for the `pycontainers` package.
3. **Threshold:** CI enforces **100%** line coverage via `COVERAGE_FAIL_UNDER` (default). The unit-test suite uses `coverage run` for accurate measurement.
4. **CI reporting:**
   - Markdown coverage summary in the GitHub Actions job summary
   - Pull request comment via `py-cov-action/python-coverage-comment-action`
   - `coverage.xml` uploaded as a workflow artifact
5. **Scope:** The unit-test job enforces coverage. Backend integration jobs (`docker`, `podman`, `container`) continue to run separately and are not included in the threshold today.

## Consequences

- Coverage regressions in unit tests fail CI.
- Pull requests show line-level coverage deltas without external services.
- The threshold must be updated manually as coverage improves.
- Integration-only code paths remain partially uncovered until backend jobs contribute to a combined report.
