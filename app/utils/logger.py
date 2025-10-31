"""Structured logging configuration."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings


def add_log_level(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application context to logs."""
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def configure_logging() -> None:
    """Configure structured logging."""

    # Common processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        add_app_context,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if settings.is_development:
        # Development: use ConsoleRenderer with colors
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Production: use JSON
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level),
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Configure logging on module import
configure_logging()

# Default logger
logger = get_logger(__name__)
