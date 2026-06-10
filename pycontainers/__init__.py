__version__ = "1.0.0"
__all__ = (
    "__version__",
    "docker",
    "PyContainers",
    "Container",
)

import logging

from pycontainers.features.docker import Container, PyContainers

docker = PyContainers()

logger = logging.getLogger("pycontainers")
logger.addHandler(logging.NullHandler())
