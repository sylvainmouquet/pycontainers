import re
import shlex

def clean_result(text:str) -> str:
    return re.sub(r'\[exit \d+\]\n?$', '', text)

def get_exit_code(text: str) -> int:
    """Return the exitcode in [exit XXX]."""
    # Take last 20 characters
    last_20 = text[-20:]

    # Extract [exit N] using regex
    match = re.search(r'\[exit (\d+)\]', last_20)
    if match:
        exit_code = int(match.group(1))
        return exit_code
    return -1


def _build_command_line(cmd_name: str, *args, **kwargs) -> str:
    """Build command line string from arguments."""
    cmd_parts = [cmd_name]

    # Add positional arguments
    for arg in args:
        if arg == "filters":
            arg = "filter"
        if arg == 'image':
            cmd_parts.append(arg)
            continue
        if isinstance(arg, dict):
            # Handle dictionary arguments - convert to command line flags
            for key, value in arg.items():
                if isinstance(value, bool) and value:
                    cmd_parts.append(f"--{key}")
                elif isinstance(value, bool) and not value:
                    # Skip false boolean flags
                    continue
                elif value is not None:
                    cmd_parts.extend([f"--{key}", str(value)])
        else:
            if hasattr(arg, "ID"):
                cmd_parts.append(str(arg.ID))
            else:
                cmd_parts.append(str(arg))

    # Add keyword arguments as flags
    for key, value in kwargs.items():
        if key == "command":
            cmd_parts.extend(value)
            continue

        if key == 'image':
            cmd_parts.append(value)
            continue

        if key == "filters":
            key = "filter"

        key_formatted = key.replace("_", "-")  # Convert underscores to hyphens
        if isinstance(value, bool) and value:
            cmd_parts.insert(1, f"--{key_formatted}")
        elif isinstance(value, bool) and not value:
            # Skip false boolean flags
            continue
        elif isinstance(value, dict) and value:
            multiple_values = f" --{key_formatted} ".join(
                f"{key}={v}" for key, v in value.items()
            )
            cmd_parts.insert(1, f"--{key_formatted} {multiple_values}")
        elif value is not None:
            cmd_parts.insert(1, f"--{key_formatted} {value}")

    if cmd_name == "ps":
        cmd_parts.insert(1, "--format=json --no-trunc")
    return shlex.split(" ".join(cmd_parts))
