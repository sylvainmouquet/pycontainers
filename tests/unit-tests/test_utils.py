from pycontainers.shared.utilities import (
    _build_command_line,
    clean_result,
    extract_run_container_id,
    get_exit_code,
    parse_container_ps_json,
    run_coro_in_thread,
)


def test_build_command_line_simple():
    assert _build_command_line("ps") == ["ps", "--format=json", "--no-trunc"]


def test_run_coro_in_thread():
    async def value():
        return "ok"

    assert run_coro_in_thread(value()) == "ok"


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


def test_parse_container_ps_json_docker_ndjson():
    row_one = '{"ID":"abc","Names":"demo"}'
    row_two = '{"ID":"def","Names":"other"}'
    rows = parse_container_ps_json(f"{row_one}\n{row_two}\n")
    assert rows == [{"ID": "abc", "Names": "demo"}, {"ID": "def", "Names": "other"}]


def test_parse_container_ps_json_skips_blank_ndjson_lines():
    row_one = '{"ID":"abc","Names":"demo"}'
    row_two = '{"ID":"def","Names":"other"}'
    rows = parse_container_ps_json(f"{row_one}\n\n{row_two}\n")
    assert rows == [{"ID": "abc", "Names": "demo"}, {"ID": "def", "Names": "other"}]


def test_parse_container_ps_json_podman_array():
    payload = '[{"ID":"abc","Names":"demo"},{"ID":"def","Names":"other"}]'
    rows = parse_container_ps_json(payload)
    assert rows == [{"ID": "abc", "Names": "demo"}, {"ID": "def", "Names": "other"}]


def test_parse_container_ps_json_podman_array_with_crlf():
    payload = '[{"ID":"abc","Names":"demo"}]\r\n'
    rows = parse_container_ps_json(payload)
    assert rows == [{"ID": "abc", "Names": "demo"}]


def test_parse_container_ps_json_empty():
    assert parse_container_ps_json("") == []


def test_extract_run_container_id_simple():
    assert extract_run_container_id("abc123\n") == "abc123"


def test_extract_run_container_id_empty_result():
    assert extract_run_container_id("") == ""


def test_extract_run_container_id_podman_pull_output():
    output = (
        'Resolved "alpine" as an alias (/etc/containers/registries.conf.d/shortnames.conf)\r\n'
        "Trying to pull docker.io/library/alpine:latest...\r\n"
        "Writing manifest to image destination\r\n"
        "2c501d5004d3d59304930ec25537b948e3a8ec73926e9403d30f056b2593cc18"
    )
    assert (
        extract_run_container_id(output)
        == "2c501d5004d3d59304930ec25537b948e3a8ec73926e9403d30f056b2593cc18"
    )


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


def test_build_command_line_positional_dict_mixed_value_types():
    assert _build_command_line("ps", {"all": True, "quiet": "true"}) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--all",
        "--quiet",
        "true",
    ]


def test_build_command_line_multiple_scalar_kwargs():
    assert _build_command_line("pull", "alpine", quiet=False, format="json") == [
        "pull",
        "--format",
        "json",
        "alpine",
    ]


def test_build_command_line_positional_dict_multiple_keys():
    assert _build_command_line("ps", {"all": True, "name": "web"}) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--all",
        "--name",
        "web",
    ]


def test_build_command_line_skips_volume_without_container_path():
    assert _build_command_line(
        "run",
        image="busybox",
        volumes={"/skip": {"mode": "rw"}},
    ) == ["run", "busybox"]


def test_build_command_line_skips_false_generic_bool():
    assert _build_command_line("pull", "alpine", quiet=False) == ["pull", "alpine"]


def test_build_command_line_skips_false_positional_dict_values():
    assert _build_command_line("ps", {"all": True, "quiet": False}) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--all",
    ]


def test_build_command_line_empty_option_dict_falls_back_to_scalar():
    assert _build_command_line("pull", "alpine", labels={}) == [
        "pull",
        "--labels",
        "{}",
        "alpine",
    ]


def test_build_command_line_run_without_image():
    assert _build_command_line("run", rm=True, command=["echo", "hi"]) == [
        "run",
        "--rm",
        "echo",
        "hi",
    ]


def test_build_command_line_volume_dict_without_mode_branch():
    assert _build_command_line(
        "run",
        image="busybox",
        volumes={"/host": {"bind": "/container"}},
    ) == ["run", "-v", "/host:/container", "busybox"]
    assert _build_command_line("version", format="json") == [
        "version",
        "--format",
        "json",
    ]


def test_build_command_line_with_positional_dict_string_value():
    assert _build_command_line("ps", {"quiet": "true"}) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--quiet",
        "true",
    ]


def test_build_command_line_with_command_string():
    assert _build_command_line("run", "busybox", command="echo hello") == [
        "run",
        "busybox",
        "echo",
        "hello",
    ]


def test_build_command_line_volume_dict_target_without_mode():
    assert _build_command_line(
        "run",
        image="busybox",
        volumes={"/host": {"target": "/container"}},
    ) == ["run", "-v", "/host:/container", "busybox"]


def test_build_command_line_volume_dict_scalar_mount():
    assert _build_command_line(
        "run",
        image="busybox",
        volumes={"/host": "/container"},
    ) == ["run", "-v", "/host:/container", "busybox"]


def test_build_command_line_generic_bool_option():
    assert _build_command_line("network", "create", internal=True) == [
        "network",
        "--internal",
        "create",
    ]


def test_build_command_line_non_ps_non_run_command():
    assert _build_command_line("pull", "alpine", quiet=True) == [
        "pull",
        "--quiet",
        "alpine",
    ]
    assert _build_command_line("ps", {"all": True, "quiet": False}) == [
        "ps",
        "--format=json",
        "--no-trunc",
        "--all",
    ]


def test_build_command_line_with_object_id_arg():
    class FakeContainer:
        ID = "container-123"

    assert _build_command_line("rm", FakeContainer()) == ["rm", "container-123"]


def test_build_command_line_with_command_list():
    assert _build_command_line("run", "busybox", command=["echo", "hello"]) == [
        "run",
        "busybox",
        "echo",
        "hello",
    ]


def test_build_command_line_volume_dict_target_and_skip_invalid():
    kwargs = {
        "image": "busybox",
        "volumes": {
            "/host": {"target": "/container", "mode": "ro"},
            "/skip": {"mode": "rw"},
        },
    }
    assert _build_command_line("run", **kwargs) == [
        "run",
        "-v",
        "/host:/container:ro",
        "busybox",
    ]


def test_build_command_line_volume_tuple_with_mode_and_scalar():
    kwargs = {
        "image": "busybox",
        "volumes": [
            ("/a", "/b", "rw"),
            "/mounted",
        ],
    }
    assert _build_command_line("run", **kwargs) == [
        "run",
        "-v",
        "/a:/b:rw",
        "-v",
        "/mounted",
        "busybox",
    ]


def test_build_command_line_generic_dict_option():
    assert _build_command_line("network", "create", labels={"env": "dev"}) == [
        "network",
        "--labels",
        "env=dev",
        "create",
    ]


def test_build_command_line_strips_quoted_shell_command():
    assert _build_command_line(
        "exec",
        "container-id",
        "sh",
        "-c",
        "'echo hello world'",
    ) == ["exec", "container-id", "sh", "-c", "echo hello world"]
