from pycontainers import CommandError, PyContainersError, UnsupportedBackendError
from pycontainers.shared.runtime.types import (
    collect_ps_kwargs,
    collect_pull_kwargs,
    collect_run_kwargs,
)


def test_command_error_attributes():
    error = CommandError("run", 125, "invalid reference format\n")

    assert isinstance(error, PyContainersError)
    assert isinstance(error, ValueError)
    assert error.subcommand == "run"
    assert error.exit_code == 125
    assert error.output == "invalid reference format\n"
    assert "run failed with exit code 125" in str(error)


def test_unsupported_backend_error_attributes():
    error = UnsupportedBackendError("lxc")

    assert isinstance(error, PyContainersError)
    assert isinstance(error, ValueError)
    assert error.backend == "lxc"
    assert "Unsupported backend: 'lxc'" in str(error)


def test_collect_run_kwargs_only_sets_truthy_values():
    kwargs = collect_run_kwargs(name="demo", detach=True, entrypoint="/bin/sh")

    assert kwargs == {
        "name": "demo",
        "detach": True,
        "entrypoint": "/bin/sh",
    }


def test_collect_ps_kwargs_supports_filter_aliases():
    kwargs = collect_ps_kwargs(all=True, filter={"name": "^demo"})

    assert kwargs == {"all": True, "filter": {"name": "^demo"}}


def test_collect_pull_kwargs_supports_command_kwarg():
    kwargs = collect_pull_kwargs(command="ubuntu:20.04")

    assert kwargs == {"command": "ubuntu:20.04"}
