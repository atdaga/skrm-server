"""WebSocket connection manager for broadcasting messages.

This module provides a generic connection manager that can be used
for custom WebSocket endpoints that need to broadcast messages to
multiple connected clients.

Note: For Y.js collaboration, use the specialized YjsWebsocketManager
in app/core/yjs/ instead.
"""

from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for broadcasting.

    Connections are organized by channel, allowing targeted broadcasts
    to specific groups of clients (e.g., organization members, room participants).

    Example usage:
        manager = ConnectionManager()

        @router.websocket("/notifications/{org_id}")
        async def notifications(websocket: WebSocket, org_id: str):
            await manager.connect(org_id, websocket)
            try:
                while True:
                    await websocket.receive_text()  # Keep alive
            except WebSocketDisconnect:
                manager.disconnect(org_id, websocket)

        # From elsewhere in the application:
        await manager.broadcast(org_id, {"type": "notification", "message": "..."})
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and add it to a channel.

        Args:
            channel: The channel identifier (e.g., org_id, room_id)
            websocket: The WebSocket connection to add
        """
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.debug(
            "WebSocket connected",
            channel=channel,
            total_connections=len(self.active_connections[channel]),
        )

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from a channel.

        Args:
            channel: The channel identifier
            websocket: The WebSocket connection to remove
        """
        if channel in self.active_connections:
            try:
                self.active_connections[channel].remove(websocket)
                logger.debug(
                    "WebSocket disconnected",
                    channel=channel,
                    remaining_connections=len(self.active_connections[channel]),
                )
            except ValueError:  # pragma: no cover
                # Connection not in list, already removed
                pass

            # Clean up empty channels
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def send_personal(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> None:  # pragma: no cover
        """Send a message to a specific WebSocket connection.

        Args:
            websocket: The target WebSocket connection
            message: The message to send (will be JSON serialized)
        """
        await websocket.send_json(message)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections in a channel.

        Failed sends are logged but don't stop the broadcast to other connections.

        Args:
            channel: The channel to broadcast to
            message: The message to send (will be JSON serialized)
        """
        if channel not in self.active_connections:
            return  # pragma: no cover

        disconnected: list[WebSocket] = []

        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send message to WebSocket",
                    channel=channel,
                    error=str(e),
                )
                disconnected.append(connection)

        # Clean up failed connections
        for conn in disconnected:
            self.disconnect(channel, conn)

    def get_connection_count(self, channel: str) -> int:
        """Get the number of active connections in a channel.

        Args:
            channel: The channel to check

        Returns:
            Number of active connections in the channel
        """
        return len(self.active_connections.get(channel, []))

    def get_total_connections(self) -> int:
        """Get the total number of active connections across all channels.

        Returns:
            Total number of active connections
        """
        return sum(len(conns) for conns in self.active_connections.values())


# Global singleton instance for general-purpose WebSocket broadcasting
ws_manager = ConnectionManager()


__all__ = ["ConnectionManager", "ws_manager"]
