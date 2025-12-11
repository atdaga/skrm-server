"""WebSocket authentication utilities.

Provides shared JWT validation for all WebSocket endpoints.
"""

from uuid import UUID

from fastapi import WebSocket

from app.core.auth import verify_token


async def validate_websocket_token(  # pragma: no cover
    websocket: WebSocket, token: str
) -> UUID | None:
    """Validate JWT token for WebSocket connection.

    This function validates a JWT token and returns the user ID if valid.
    If the token is invalid or expired, it closes the WebSocket connection
    with an appropriate error code.

    WebSocket close codes used:
    - 4001: Invalid token
    - 4002: Token expired (currently handled same as invalid)

    Args:
        websocket: The WebSocket connection to validate
        token: The JWT token to validate

    Returns:
        The user ID (UUID) if the token is valid, None otherwise.
        If None is returned, the WebSocket has been closed.

    Example:
        @router.websocket("/{room_id}")
        async def websocket_endpoint(
            websocket: WebSocket,
            room_id: str,
            token: str = Query(...),
        ):
            user_id = await validate_websocket_token(websocket, token)
            if not user_id:
                return  # WebSocket already closed

            # Continue with authenticated connection...
    """
    payload = await verify_token(token)

    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return None

    # Extract user ID from token payload
    sub = payload.get("sub")
    if not sub:
        await websocket.close(code=4001, reason="Invalid token: missing subject")
        return None

    try:
        return UUID(sub)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid token: invalid user ID")
        return None


__all__ = ["validate_websocket_token"]
