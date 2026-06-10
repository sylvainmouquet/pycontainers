# Show available recipes
default:
    @just --list

# Commit and push work in progress
wip:
    git add .
    git commit -m "WIP: Work in progress"
    git push

# Install dependencies
install:
    uv sync --python ${PYTHON_VERSION:-3.14} --all-extras --dev

# Build the project (requires VERSION env var)
build: check-version
    rm -rf dist/* || true
    ./scripts/version.sh "${VERSION}"
    @cat pyproject.toml | grep version
    @cat pycontainers/__init__.py | grep version
    uv build --python ${PYTHON_VERSION:-3.14}

[private]
check-version:
    #!/usr/bin/env bash
    if [ -z "${VERSION}" ]; then
        echo "VERSION is not set. Please set the VERSION environment variable."
        exit 1
    fi

# Run pyright
check:
    echo "Run pyright"
    PYRIGHT_PYTHON_FORCE_VERSION=latest uv run pyright

# Deploy to PyPI
deploy:
    uvx twine upload dist/*

# Install the local wheel build
install-local:
    pip3 install dist/*.whl

# Run tests (optional extra args: `just test tests/unit-tests/test_foo.py`)
test *args:
    #!/usr/bin/env bash
    if [ -z "{{args}}" ]; then
        uv run --python ${PYTHON_VERSION:-3.14} pytest -v --log-cli-level=INFO
    else
        uv run --python ${PYTHON_VERSION:-3.14} pytest -v --log-cli-level=INFO {{args}}
    fi

# Run unit tests with coverage collection and threshold enforcement
test-cov *args:
    #!/usr/bin/env bash
    set -euo pipefail
    COVERAGE_FAIL_UNDER="${COVERAGE_FAIL_UNDER:-100}"
    if [ -z "{{args}}" ]; then
        TEST_ARGS=(tests/unit-tests/)
    else
        TEST_ARGS=( {{args}} )
    fi
    uv run coverage run -m pytest -v --log-cli-level=INFO "${TEST_ARGS[@]}"
    uv run coverage report --fail-under="${COVERAGE_FAIL_UNDER}"
    uv run coverage xml -o coverage.xml

# Run backend-specific integration tests
test-docker:
    uv run --python ${PYTHON_VERSION:-3.14} pytest -v tests/backends/docker/

test-container:
    uv run --python ${PYTHON_VERSION:-3.14} pytest -v tests/backends/container/

test-podman:
    uv run --python ${PYTHON_VERSION:-3.14} pytest -v tests/backends/podman/

# Run the formatter
format:
    uv run ruff format

# Run linter and verify formatting
lint: format
    uv run ruff check --fix
    uv run ruff format --check

# Run the Docker usage example (smoke test for local install)
example-docker:
    timeout 30 uv run --python ${PYTHON_VERSION:-3.14} python3 -m examples.docker.example_docker

# Update dependencies
update:
    uv lock --upgrade
    uv sync

# Check for outdated dependencies
check-deps:
    .venv/bin/pip list --outdated
