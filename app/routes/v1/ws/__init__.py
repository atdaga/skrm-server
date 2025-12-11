"""WebSocket routes for real-time collaboration.

This module provides WebSocket endpoints for:
- Y.js document collaboration (via pycrdt-websocket)
- Future: Notifications, presence, custom payloads
"""

from fastapi import APIRouter

from . import collab

router = APIRouter(prefix="/ws", tags=["websocket"])

# Y.js document collaboration
router.include_router(collab.router)

# Future endpoints:
# router.include_router(notify.router)
# router.include_router(presence.router)


__all__ = ["router"]
