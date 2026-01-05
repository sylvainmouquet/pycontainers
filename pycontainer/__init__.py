__version__ = "1.0.0"
__all__ = (
    "__version__",
    "docker",
)

import logging

from pycontainer.pycontainer import PyContainer


docker = PyContainer()

logger = logging.getLogger("pycontainer")
logger.addHandler(logging.NullHandler())

