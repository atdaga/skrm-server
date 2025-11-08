import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from ..config import settings
from .context import get_principal_id, get_request_id, get_request_time


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add the log level to the event dict."""
    if method_name == "info":
        event_dict["level"] = "INFO"
    elif method_name == "debug":
        event_dict["level"] = "DEBUG"
    elif method_name == "warning":
        event_dict["level"] = "WARNING"
    elif method_name == "error":
        event_dict["level"] = "ERROR"
    elif method_name == "critical":
        event_dict["level"] = "CRITICAL"
    return event_dict


def add_request_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add request context variables to the event dict.

    This processor automatically includes request_id, principal_id, and request_time
    in all log messages when available from the request context.
    """
    request_id = get_request_id()
    principal_id = get_principal_id()
    request_time = get_request_time()

    if request_id is not None:
        event_dict["request_id"] = str(request_id)

    if principal_id is not None:
        event_dict["principal_id"] = principal_id

    if request_time is not None:
        event_dict["request_time"] = request_time.isoformat()

    return event_dict


def setup_logging() -> None:
    """Configure structlog for the application."""
    # TODO: fmt is local for development, but UTC for production
    timestamper = structlog.processors.TimeStamper(fmt="ISO")

    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        add_log_level,
        structlog.stdlib.add_log_level,
        add_request_context,  # Add request context (request_id, principal_id, request_time)
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


def get_logger(name: str) -> Any:
    """Get a configured logger instance."""
    return structlog.get_logger(name)
