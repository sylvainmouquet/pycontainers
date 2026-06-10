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


def test_pycontainers_error_is_exception():
    assert issubclass(PyContainersError, Exception)


def test_collect_run_kwargs_all_options():
    kwargs = collect_run_kwargs(
        name="demo",
        detach=True,
        rm=True,
        entrypoint="/bin/sh",
        command=["-c", "echo hi"],
        envs={"A": "1"},
        volumes={"/host": "/container"},
        expose=[8080],
        publish=[(8080, 80)],
        cap_add=["NET_ADMIN"],
        extra={"network": "bridge"},
    )
    assert kwargs["name"] == "demo"
    assert kwargs["detach"] is True
    assert kwargs["rm"] is True
    assert kwargs["entrypoint"] == "/bin/sh"
    assert kwargs["command"] == ["-c", "echo hi"]
    assert kwargs["envs"] == {"A": "1"}
    assert kwargs["volumes"] == {"/host": "/container"}
    assert kwargs["expose"] == [8080]
    assert kwargs["publish"] == [(8080, 80)]
    assert kwargs["cap_add"] == ["NET_ADMIN"]
    assert kwargs["network"] == "bridge"


def test_collect_ps_kwargs_with_filters_and_extra():
    kwargs = collect_ps_kwargs(all=True, filters={"status": "running"}, extra={"quiet": True})
    assert kwargs == {"all": True, "filters": {"status": "running"}, "quiet": True}


def test_collect_pull_kwargs_with_extra():
    kwargs = collect_pull_kwargs(extra={"quiet": True})
    assert kwargs == {"quiet": True}
