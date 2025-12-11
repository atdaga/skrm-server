"""Y.js document collaboration WebSocket endpoint.

This module provides the WebSocket endpoint for real-time collaborative
editing using the Y.js CRDT protocol via pycrdt-websocket.
"""

from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.db.database import get_db_session
from app.core.exceptions.domain_exceptions import (
    UnauthorizedOrganizationAccessException,
)
from app.core.logging import get_logger
from app.core.websocket.auth import validate_websocket_token
from app.core.yjs import yjs_manager
from app.logic.v1 import yjs_collab

logger = get_logger(__name__)

router = APIRouter(prefix="/collab", tags=["collaboration"])


class FastAPIWebSocketChannel:  # pragma: no cover
    """Adapter to make FastAPI WebSocket compatible with pycrdt Channel protocol.

    This wraps a FastAPI WebSocket to provide the interface expected by
    pycrdt-websocket's YRoom.serve() method.
    """

    def __init__(self, websocket: WebSocket, path: str) -> None:
        self._websocket = websocket
        self._path = path

    @property
    def path(self) -> str:
        """The channel path (document ID)."""
        return self._path

    def __aiter__(self) -> FastAPIWebSocketChannel:
        return self

    async def __anext__(self) -> bytes:
        return await self.recv()

    async def send(self, message: bytes) -> None:
        """Send a message through the WebSocket."""
        await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        """Receive a message from the WebSocket."""
        return await self._websocket.receive_bytes()


@router.websocket("/{doc_id}")
async def yjs_websocket_endpoint(  # pragma: no cover
    websocket: WebSocket,
    doc_id: UUID,
    token: str = Query(..., description="JWT authentication token"),
) -> None:
    """WebSocket endpoint for Y.js document collaboration.

    This endpoint handles real-time collaborative editing for documents.
    It uses the Y.js CRDT protocol to synchronize changes between clients.

    Authentication is done via JWT token in query parameter.
    The user must be a member of the organization that owns the document.

    Args:
        websocket: The WebSocket connection
        doc_id: The document ID to collaborate on
        token: JWT authentication token

    WebSocket Close Codes:
        4001: Invalid or expired token
        4004: Document not found
        4003: User not authorized to access document
    """
    # 1. Validate JWT token
    user_id = await validate_websocket_token(websocket, token)
    if user_id is None:
        return  # WebSocket already closed by validate_websocket_token

    # 2. Get document and verify access using logic layer
    async with get_db_session() as db:
        try:
            doc = await yjs_collab.get_doc_for_collab(doc_id, user_id, db)
        except UnauthorizedOrganizationAccessException:
            await websocket.close(
                code=4003, reason="Not authorized to access this document"
            )
            return

        if doc is None:
            await websocket.close(code=4004, reason="Document not found")
            return

    # 3. Get or create room with PostgreSQL persistence
    room = await yjs_manager.get_or_create_room(
        doc_id=doc.id,
        org_id=doc.org_id,
        user_id=user_id,
    )

    # 4. Accept WebSocket and handle Y.js sync
    await websocket.accept()

    logger.info(
        "Y.js WebSocket connected",
        doc_id=str(doc_id),
        user_id=str(user_id),
    )

    try:
        # Wrap FastAPI WebSocket for pycrdt-websocket using our Channel adapter
        channel = FastAPIWebSocketChannel(websocket, str(doc_id))
        await room.serve(channel)
    except WebSocketDisconnect:
        logger.info(
            "Y.js WebSocket disconnected",
            doc_id=str(doc_id),
            user_id=str(user_id),
        )
    except Exception as e:
        logger.error(
            "Y.js WebSocket error",
            doc_id=str(doc_id),
            user_id=str(user_id),
            error=str(e),
        )


__all__ = ["router"]
