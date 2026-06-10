from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    get_exit_code,
)


def test_build_command_line_simple():
    assert _build_command_line("ps") == ["ps", "--format=json", "--no-trunc"]


def test_build_command_line_with_filter():
    assert _build_command_line("ps", filters={"name": "^ubuntu"}, all=True) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--all",
        "--filter",
        "name=^ubuntu",
    ]

    args = ()
    kwargs = {"all": True, "filter": {"name": "^ubuntu"}}
    assert _build_command_line("ps", *args, **kwargs) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--filter",
        "name=^ubuntu",
        "--all",
    ]


def test_build_command_line_with_filters():
    args = ()
    kwargs = {"all": True, "filters": {"name": "^ubuntu"}}
    assert _build_command_line("ps", *args, **kwargs) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--filter",
        "name=^ubuntu",
        "--all",
    ]


def test_build_command_line_with_command():
    args = ("busybox",)
    kwargs = {
        "rm": True,
        "entrypoint": "/bin/sh",
        "command": ["-c", "echo hello world"],
    }
    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "--entrypoint",
        "/bin/sh",
        "--rm",
        "busybox",
        "-c",
        "echo hello world",
    ]


def test_build_command_line_with_image():
    args = ()
    kwargs = {
        "image": "busybox",
    }
    assert _build_command_line("run", *args, **kwargs) == ["run", "busybox"]

    assert _build_command_line("run", image="busybox") == ["run", "busybox"]


def test_build_command_line_with_image_and_command():
    args = ()
    kwargs = {
        "image": "busybox",
        "rm": True,
        "entrypoint": "/bin/sh",
        "command": ["-c", "echo hello world"],
    }
    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "--entrypoint",
        "/bin/sh",
        "--rm",
        "busybox",
        "-c",
        "echo hello world",
    ]

    assert _build_command_line(
        "run", image="busybox", command=["-c", "echo hello world"]
    ) == ["run", "busybox", "-c", "echo hello world"]


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


def test_build_command_line_with_volumes():
    args = ()
    kwargs = {
        "image": "busybox",
        "volumes": [("/a.sh", "/b.sh"), ("/c.json", "/d.json")],
    }
    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "-v",
        "/a.sh:/b.sh",
        "-v",
        "/c.json:/d.json",
        "busybox",
    ]


def test_build_command_line_with_volumes_dict():
    args = ()
    kwargs = {
        "image": "busybox",
        "volumes": {"/a.sh": {"bind": "/b.sh", "mode": "rw"}},
    }
    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "-v",
        "/a.sh:/b.sh:rw",
        "busybox",
    ]


def test_build_command_line_with_ports():
    args = ()
    kwargs = {"image": "busybox", "expose": [8200, 8900], "publish": [(8201, 8202)]}
    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "--expose",
        "8200",
        "--expose",
        "8900",
        "-p",
        "8201:8202",
        "busybox",
    ]


def test_build_command_line_with_envs():
    args = ()
    kwargs = {
        "image": "busybox",
        "envs": {
            "var1": "one",
            "var2": "two",
            "var3": "three",
        },
    }

    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "-e",
        "var1=one",
        "-e",
        "var2=two",
        "-e",
        "var3=three",
        "busybox",
    ]


def test_build_command_line_with_cap_add():
    args = ()
    kwargs = {"image": "busybox", "cap_add": ["FIRST", "SECOND"]}

    assert _build_command_line("run", *args, **kwargs) == [
        "run",
        "--cap-add=FIRST",
        "--cap-add=SECOND",
        "busybox",
    ]
