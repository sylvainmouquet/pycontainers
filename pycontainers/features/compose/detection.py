import shutil
import subprocess

from pycontainers.shared.runtime.detection import RuntimeBackend
from pycontainers.shared.runtime.macos_commands import uses_macos_container_cli


def is_compose_available(backend: RuntimeBackend = "docker") -> bool:
    """Return True when the runtime CLI supports compose subcommands."""
    if uses_macos_container_cli(backend):
        return False
    if shutil.which(backend) is None:
        return False

    result = subprocess.run(
        [backend, "compose", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
