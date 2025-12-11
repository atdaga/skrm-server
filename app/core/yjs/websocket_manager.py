"""Y.js WebSocket server manager.

This module provides lifecycle management for the pycrdt-websocket server,
integrating with FastAPI's lifespan and providing room management with
PostgreSQL persistence.
"""

import asyncio
from asyncio import Task
from uuid import UUID

from pycrdt.websocket import WebsocketServer
from pycrdt.websocket.websocket_server import YRoom

from app.core.db.database import get_db_session
from app.core.logging import get_logger

from .postgres_ystore import PostgresYStore

logger = get_logger(__name__)


class YjsWebsocketManager:
    """Manages Y.js WebSocket server and room lifecycle.

    This class wraps the pycrdt WebsocketServer and provides:
    - Server lifecycle management (start/stop) for FastAPI lifespan integration
    - Room creation with PostgreSQL persistence
    - Custom exception handling for Y.js operations

    Example usage in FastAPI lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await yjs_manager.start()
            yield
            await yjs_manager.stop()
    """

    def __init__(self) -> None:
        """Initialize the Y.js WebSocket manager."""
        self._websocket_server: WebsocketServer | None = None
        self._server_task: Task[None] | None = None
        self._rooms: dict[str, YRoom] = {}

    @property
    def websocket_server(self) -> WebsocketServer:  # pragma: no cover
        """Get the WebSocket server instance.

        Raises:
            RuntimeError: If the server has not been started.
        """
        if self._websocket_server is None:
            raise RuntimeError("Y.js WebSocket server not started")
        return self._websocket_server

    async def start(self) -> None:
        """Start the Y.js WebSocket server.

        This should be called during FastAPI application startup.
        Uses asyncio.create_task() to run the server in the background,
        allowing the calling code to continue execution.
        """
        if self._websocket_server is not None:
            logger.warning("Y.js WebSocket server already started")
            return

        self._websocket_server = WebsocketServer()
        # Create a background task for the server (start() blocks until stop() is called)
        self._server_task = asyncio.create_task(self._websocket_server.start())
        # Wait for the server to be ready
        await self._websocket_server.started.wait()
        logger.info("Y.js WebSocket server started")

    async def stop(self) -> None:
        """Stop the Y.js WebSocket server.

        This should be called during FastAPI application shutdown.
        Stops all rooms and the server itself.
        """
        if self._websocket_server is None:
            return

        # Stop all rooms
        for room_name, room in list(self._rooms.items()):  # pragma: no cover
            try:
                await room.stop()
                logger.debug("Stopped Y.js room", room_name=room_name)
            except Exception as e:
                logger.warning(
                    "Error stopping Y.js room",
                    room_name=room_name,
                    error=str(e),
                )

        self._rooms.clear()

        # Stop the server
        try:
            await self._websocket_server.stop()
            logger.info("Y.js WebSocket server stopped")
        except Exception as e:  # pragma: no cover
            logger.warning("Error stopping Y.js WebSocket server", error=str(e))

        # Wait for the background task to complete
        if self._server_task is not None:
            try:
                await self._server_task
            except asyncio.CancelledError:  # pragma: no cover
                pass  # Expected when stop() cancels the task
            except Exception as e:  # pragma: no cover
                logger.warning("Error waiting for server task", error=str(e))
            finally:
                self._server_task = None

        self._websocket_server = None

    def _handle_room_exception(  # pragma: no cover
        self, exception: Exception, log: object
    ) -> bool:
        """Handle exceptions from Y.js room operations.

        Args:
            exception: The exception that occurred
            log: Logger instance (from pycrdt)

        Returns:
            True if the exception was handled and the room should continue,
            False if the room should be stopped.
        """
        logger.error(
            "Y.js room exception",
            error=str(exception),
            error_type=type(exception).__name__,
        )
        # Return False to stop the room on unhandled exceptions
        return False

    async def get_or_create_room(  # pragma: no cover
        self,
        doc_id: UUID,
        org_id: UUID,
        user_id: UUID,
        document_ttl: int | None = 3600,
    ) -> YRoom:
        """Get or create a Y.js room with PostgreSQL persistence.

        If a room already exists for the document, it is returned.
        Otherwise, a new room is created with a PostgresYStore for persistence.

        Args:
            doc_id: The document ID (used as room name and for persistence)
            org_id: The organization ID (for audit trail)
            user_id: The user ID (for audit trail on stored updates)
            document_ttl: Time in seconds before old updates are compacted

        Returns:
            The Y.js room instance
        """
        room_name = str(doc_id)

        # Check if room already exists
        if room_name in self._rooms:
            return self._rooms[room_name]

        # Create store with PostgreSQL persistence
        ystore = PostgresYStore(
            path=room_name,
            doc_id=doc_id,
            org_id=org_id,
            user_id=user_id,
            db_session_factory=get_db_session,
            document_ttl=document_ttl,
        )

        # Create room with the store
        room = YRoom(
            ystore=ystore,
            exception_handler=self._handle_room_exception,
        )

        # Start the room
        await room.start()

        # Track the room
        self._rooms[room_name] = room

        logger.info(
            "Created Y.js room",
            room_name=room_name,
            doc_id=str(doc_id),
            org_id=str(org_id),
        )

        return room

    async def delete_room(self, doc_id: UUID) -> None:  # pragma: no cover
        """Delete a Y.js room and stop its processing.

        Args:
            doc_id: The document ID of the room to delete
        """
        room_name = str(doc_id)

        if room_name not in self._rooms:
            return

        room = self._rooms.pop(room_name)
        await room.stop()

        logger.info("Deleted Y.js room", room_name=room_name)

    def get_room_count(self) -> int:
        """Get the number of active rooms.

        Returns:
            Number of active Y.js rooms
        """
        return len(self._rooms)

    def has_room(self, doc_id: UUID) -> bool:
        """Check if a room exists for a document.

        Args:
            doc_id: The document ID to check

        Returns:
            True if a room exists, False otherwise
        """
        return str(doc_id) in self._rooms


# Global singleton instance
yjs_manager = YjsWebsocketManager()


__all__ = ["YjsWebsocketManager", "yjs_manager"]
