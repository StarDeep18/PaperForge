"""
PaperForge Structured Logging.

Provides a configured logger with structured output format.
Uses standard library logging with custom formatting for
development readability and production JSON compatibility.
"""

import logging
import sys
from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    """
    Configure and return the application logger.

    In development: human-readable colored format.
    In production: structured format suitable for log aggregation.
    """
    settings = get_settings()

    logger = logging.getLogger("paperforge")
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        if settings.is_production:
            formatter = logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"module":"%(module)s","message":"%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "\033[36m%(asctime)s\033[0m │ "
                "\033[1m%(levelname)-8s\033[0m │ "
                "\033[33m%(name)s.%(module)s\033[0m │ "
                "%(message)s",
                datefmt="%H:%M:%S",
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
