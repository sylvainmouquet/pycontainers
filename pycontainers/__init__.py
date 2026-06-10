__version__ = "1.0.0"
__all__ = (
    "__version__",
    "docker",
    "podman",
    "PyContainers",
    "Container",
    "ComposeClient",
    "ComposeService",
    "detect_runtime",
    "CommandError",
    "PyContainersError",
    "UnsupportedBackendError",
)

import logging

from pycontainers.features.compose import ComposeClient, ComposeService
from pycontainers.shared.errors import (
    CommandError,
    PyContainersError,
    UnsupportedBackendError,
)
from pycontainers.shared.runtime.client import PyContainers
from pycontainers.shared.runtime.container import Container
from pycontainers.shared.runtime.detection import detect_runtime

docker = PyContainers(backend="docker")
podman = PyContainers(backend="podman")

logger = logging.getLogger("pycontainers")
logger.addHandler(logging.NullHandler())
