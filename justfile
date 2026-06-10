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
    uv sync --python ${PYTHON_VERSION:-3.13} --all-extras --dev

# Build the project (requires VERSION env var)
build: check-version
    rm -rf dist/* || true
    ./scripts/version.sh "${VERSION}"
    @cat pyproject.toml | grep version
    @cat pycontainers/__init__.py | grep version
    uv build --python ${PYTHON_VERSION:-3.13}

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
        uv run --python ${PYTHON_VERSION:-3.13} pytest -v --log-cli-level=INFO
    else
        uv run --python ${PYTHON_VERSION:-3.13} pytest -v --log-cli-level=INFO {{args}}
    fi

# Run linter and formatter
lint:
    uv run ruff check --fix
    uv run ruff format
    uv run ruff format --check

# Update dependencies
update:
    uv lock --upgrade
    uv sync

# Check for outdated dependencies
check-deps:
    .venv/bin/pip list --outdated
