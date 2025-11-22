"""Request context variables for tracking request-scoped data.

This module provides context variables that are automatically populated by middleware
and can be accessed throughout the request lifecycle for logging, auditing, and business logic.
"""

from contextvars import ContextVar
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

# Context variables for request-scoped data
request_id_var: ContextVar[UUID | None] = ContextVar("request_id", default=None)
principal_id_var: ContextVar[str | None] = ContextVar("principal_id", default=None)
request_time_var: ContextVar[datetime | None] = ContextVar("request_time", default=None)


class RequestContext(NamedTuple):
    """Container for all request context values."""

    request_id: UUID | None
    principal_id: str | None
    request_time: datetime | None

    def __repr__(self) -> str:
        """Generate a readable repr for RequestContext."""
        request_id_str = repr(str(self.request_id)) if self.request_id else "None"
        request_time_str = (
            repr(self.request_time.isoformat()) if self.request_time else "None"
        )
        return (
            f"RequestContext(request_id={request_id_str}, "
            f"principal_id={self.principal_id!r}, "
            f"request_time={request_time_str})"
        )


def get_request_id() -> UUID | None:
    """Get the current request ID from context.

    Returns:
        UUID of the current request, or None if not set.
    """
    return request_id_var.get()


def get_principal_id() -> str | None:
    """Get the current principal (user) ID from context.

    Returns:
        Principal ID extracted from JWT token, or None if not authenticated.
    """
    return principal_id_var.get()


def get_request_time() -> datetime | None:
    """Get the current request timestamp from context.

    Returns:
        UTC timestamp when the request started, or None if not set.
    """
    return request_time_var.get()


def get_request_context() -> RequestContext:
    """Get all request context values as a single object.

    Returns:
        RequestContext containing request_id, principal_id, and request_time.
    """
    return RequestContext(
        request_id=request_id_var.get(),
        principal_id=principal_id_var.get(),
        request_time=request_time_var.get(),
    )
