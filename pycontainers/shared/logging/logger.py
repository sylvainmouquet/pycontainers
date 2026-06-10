import logging
import sys

import structlog
from structlog.typing import FilteringBoundLogger


def setup_structlog(
    log_level: str = "INFO",
    json_logs: bool = True,
    include_timestamp: bool = True,
) -> None:
    """
    Configure structlog for structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
        include_timestamp: Whether to include timestamps in logs
    """

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="ISO", utc=True))

    if json_logs:
        processors.extend(
            [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
        )
    else:
        processors.extend([structlog.dev.ConsoleRenderer(colors=True)])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
