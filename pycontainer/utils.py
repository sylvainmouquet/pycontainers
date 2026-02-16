import re
import shlex


def clean_result(text: str) -> str:
    return re.sub(r"\[exit \d+\]\n?$", "", text)


def get_exit_code(text: str) -> int:
    """Return the exitcode in [exit XXX]."""
    # Take last 20 characters
    last_20 = text[-20:]

    # Extract [exit N] using regex
    match = re.search(r"\[exit (\d+)\]", last_20)
    if match:
        exit_code = int(match.group(1))
        return exit_code
    return -1


def _build_command_line(cmd_name: str, *args, **kwargs) -> list[str]:
    """Build command line string from arguments."""
    cmd_parts = [cmd_name]
    generic_options: list[str] = []
    entrypoint_options: list[str] = []
    image: str | None = None
    command: list[str] = []
    post_image_parts: list[str] = []
    positional_parts: list[str] = []

    # Positional args are kept separate so command-specific ordering stays correct.
    for arg in args:
        if isinstance(arg, dict):
            for key, value in arg.items():
                key_formatted = "filter" if key == "filters" else key.replace("_", "-")
                if isinstance(value, bool):
                    if value:
                        positional_parts.append(f"--{key_formatted}")
                elif value is not None:
                    positional_parts.extend([f"--{key_formatted}", str(value)])
            continue

        value = str(arg.ID) if hasattr(arg, "ID") else str(arg)
        if cmd_name == "run" and image is None:
            image = value
        else:
            positional_parts.append(value)

    for key, value in kwargs.items():
        if key == "command":
            if isinstance(value, str):
                command.extend(shlex.split(value))
            else:
                command.extend([str(v) for v in value])
            continue

        if key == "image":
            image = str(value)
            continue

        if key == "entrypoint":
            entrypoint_options.extend(["--entrypoint", str(value)])
            continue

        if key == "volumes":
            if isinstance(value, dict):
                for host_path, mount in value.items():
                    container_path: str | None = None
                    mode: str | None = None

                    if isinstance(mount, dict):
                        bind = mount.get("bind") or mount.get("target")
                        if bind is not None:
                            container_path = str(bind)
                        if mount.get("mode") is not None:
                            mode = str(mount["mode"])
                    elif mount is not None:
                        container_path = str(mount)

                    if container_path is None:
                        continue

                    volume_spec = f"{host_path}:{container_path}"
                    if mode:
                        volume_spec = f"{volume_spec}:{mode}"
                    post_image_parts.extend(["-v", volume_spec])
            else:
                for mount in value:
                    if isinstance(mount, (tuple, list)) and len(mount) >= 2:
                        host_path, container_path = mount[0], mount[1]
                        mode = str(mount[2]) if len(mount) >= 3 else None
                        volume_spec = f"{host_path}:{container_path}"
                        if mode:
                            volume_spec = f"{volume_spec}:{mode}"
                        post_image_parts.extend(["-v", volume_spec])
                    else:
                        post_image_parts.extend(["-v", str(mount)])
            continue

        if key == "expose":
            for port in value:
                post_image_parts.extend(["--expose", str(port)])
            continue

        if key == "publish":
            for one, two in value:
                post_image_parts.extend(["-p", f"{one}:{two}"])
            continue

        if key == "cap_add":
            for cap in value:
                post_image_parts.append(f"--cap-add={cap}")
            continue

        if key == "envs":
            for name, val in value.items():
                post_image_parts.extend(["-e", f"{name}={val}"])
            continue

        key_formatted = "filter" if key == "filters" else key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                generic_options = [f"--{key_formatted}", *generic_options]
        elif isinstance(value, dict) and value:
            option_tokens: list[str] = []
            for dict_key, dict_value in value.items():
                option_tokens.extend([f"--{key_formatted}", f"{dict_key}={dict_value}"])
            generic_options = [*option_tokens, *generic_options]
        elif value is not None:
            generic_options = [f"--{key_formatted}", str(value), *generic_options]

    if cmd_name == "ps":
        cmd_parts.extend(["--format=json", "--no-trunc"])
        cmd_parts.extend(generic_options)
        cmd_parts.extend(positional_parts)
    elif cmd_name == "run":
        cmd_parts.extend(entrypoint_options)
        cmd_parts.extend(generic_options)
        cmd_parts.extend(post_image_parts)
        if image is not None:
            cmd_parts.append(image)
        cmd_parts.extend(positional_parts)
    else:
        cmd_parts.extend(generic_options)
        cmd_parts.extend(positional_parts)
        cmd_parts.extend(post_image_parts)

    cmd_parts.extend(command)
    cmd_parts = [part for part in cmd_parts if part != ""]

    if "-c" in cmd_parts:
        idx = cmd_parts.index("-c")
        shell_cmd = " ".join(cmd_parts[idx + 1 :])
        # Normalize accidental extra wrapper quotes, e.g. "'sleep 60s'".
        if len(shell_cmd) >= 2 and (
            (shell_cmd.startswith("'") and shell_cmd.endswith("'"))
            or (shell_cmd.startswith('"') and shell_cmd.endswith('"'))
        ):
            shell_cmd = shell_cmd[1:-1]
        cmd_parts = cmd_parts[: idx + 1] + [shell_cmd]

    return cmd_parts
