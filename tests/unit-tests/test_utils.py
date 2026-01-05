from pycontainer.utils import _build_command_line, get_exit_code, clean_result


def test_build_command_line_simple():
    assert _build_command_line("ps") == ["ps", "--format=json", "--no-trunc"]


def test_build_command_line_with_filter():
    assert (
        _build_command_line("ps", filters={"name": "^ubuntu"}, all=True)
        == ["ps", "--format=json", "--no-trunc", "--all", "--filter", "name=^ubuntu"]
    )

    args = ()
    kwargs = {"all": True, "filter": {"name": "^ubuntu"}}
    assert (
        _build_command_line("ps", *args, **kwargs)
        == ["ps", "--format=json", "--no-trunc", "--filter", "name=^ubuntu", "--all"]
    )


def test_build_command_line_with_filters():
    args = ()
    kwargs = {"all": True, "filters": {"name": "^ubuntu"}}
    assert (
        _build_command_line("ps", *args, **kwargs)
        == ["ps", "--format=json", "--no-trunc", "--filter", "name=^ubuntu", "--all"]
    )


def test_build_command_line_with_command():
    args = ("busybox",)
    kwargs = {
        "rm": True,
        "entrypoint": "/bin/sh",
        "command": ["-c", "'echo hello world'"],
    }
    assert (
        _build_command_line("run", *args, **kwargs)
        == ["run", "--entrypoint", "/bin/sh", "--rm", "busybox", "-c", "echo hello world"]
    )

def test_build_command_line_with_image():
    args = ()
    kwargs = {
        "image": 'busybox',
    }
    assert (
        _build_command_line("run", *args, **kwargs)
        == ["run", "busybox"]
    )

    assert (
            _build_command_line("run", image="busybox")
            == ["run", "busybox"]
    )

def test_build_command_line_with_image_and_command():
    args = ()
    kwargs = {
        "image": 'busybox',
        "rm": True,
        "entrypoint": "/bin/sh",
        "command": ["-c", "'echo hello world'"],
    }
    assert (
        _build_command_line("run", *args, **kwargs)
        == ["run", "--entrypoint", "/bin/sh", "--rm", "busybox", "-c", "echo hello world"]
    )

    assert (
            _build_command_line("run", image="busybox", command=["-c", "'echo hello world'"])
            == ["run", "busybox", "-c", "echo hello world"]
    )

def test_get_exit_code():
    assert get_exit_code("") == -1
    assert get_exit_code("fake") == -1
    assert get_exit_code("[exit 1]") == 1
    assert get_exit_code("[exit 125]") == 125

def test_clean_result():
    assert clean_result("") == ""
    assert clean_result("[exit 1]") == ""
    assert clean_result("some output\n[exit 2]\n") == "some output\n"
    assert clean_result("no exit line here") == "no exit line here"
