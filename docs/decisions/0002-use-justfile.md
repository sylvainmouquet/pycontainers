# ADR 0002: Use Just as the task runner

## Status

Accepted

## Context

The project needs a consistent way to run build, test, lint, and release tasks locally and in CI. Makefiles are common but add portability and syntax friction on macOS and Windows. Developers already use `uv` for Python dependency management.

## Decision

Use [Just](https://github.com/casey/just) with a root `justfile` as the sole task runner for this repository.

- All repeatable development commands are defined as `just` recipes.
- CI workflows call `just` recipes instead of duplicating shell commands.
- Documentation references `just <recipe>` syntax, not `make` targets.
- No `Makefile` is maintained in this repository.

## Consequences

**Positive**

- One command surface for local development and CI.
- Recipes are easy to read, compose, and extend.
- New contributors discover tasks via `just --list`.

**Negative**

- Contributors must install Just (documented in `README.md` and `docs/development.md`).

## References

- `justfile`
- `docs/development.md`
- `.github/actions/setup/action.yml`
