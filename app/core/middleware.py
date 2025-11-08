"""Request context middleware for FastAPI.

This middleware automatically extracts request context (principal ID, request ID, timestamp)
and makes it available throughout the request lifecycle via context variables.
"""

from datetime import UTC, datetime
from uuid import uuid7

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .auth import verify_token
from .context import principal_id_var, request_id_var, request_time_var


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that populates request context variables for each request.

    This middleware:
    - Generates a unique UUID7 request ID
    - Creates a UTC timestamp for when the request started
    - Extracts the principal ID from the JWT token (if present and valid)
    - Stores all three values in context variables for use throughout the request

    Context variables are automatically cleared after the request completes.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and populate context variables.

        Args:
            request: The incoming FastAPI request
            call_next: The next middleware/handler in the chain

        Returns:
            The response from the next handler
        """
        # Generate request ID and timestamp
        request_id = uuid7()
        request_time = datetime.now(UTC).replace(tzinfo=None)

        # Extract principal ID from JWT token if present
        principal_id: str | None = None
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            payload = await verify_token(token)

            if payload is not None:
                # Extract the 'sub' claim which contains the principal/user ID
                principal_id = payload.get("sub")

                # Cache the validated token and payload for reuse in dependencies
                # This eliminates duplicate JWT validation in protected endpoints
                request.state.jwt_token = token
                request.state.jwt_payload = payload

        # Set context variables
        request_id_var.set(request_id)
        principal_id_var.set(principal_id)
        request_time_var.set(request_time)

        try:
            # Process the request
            response = await call_next(request)
            return response
        finally:
            # Context variables are automatically cleared when the context ends,
            # but we can explicitly clear them for clarity
            request_id_var.set(None)
            principal_id_var.set(None)
            request_time_var.set(None)


__all__ = ["RequestContextMiddleware"]
