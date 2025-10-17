"""
Structlog setup + standard library logging bridge.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

import structlog


def configure_logging(level: int | str = logging.INFO, pretty: bool = True) -> structlog.BoundLogger:
    """
    Configure structlog and return a bound logger.
    Call once at process start (this module also does a safe default config on import).
    """
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    # stdlib logging to stderr (so structlog ConsoleRenderer below looks nice)
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(message)s",
    )

    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    if pretty:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),  # prints to stderr
        cache_logger_on_first_use=False,
    )
    return structlog.get_logger()


# Default, safe configuration on import (keeps prior behavior)
logger: structlog.BoundLogger = configure_logging()
