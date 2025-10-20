"""V1 API router aggregating all v1 endpoints."""

from fastapi import APIRouter

from . import teams, users

# Create main v1 router
router = APIRouter()

# Include all v1 subrouters
router.include_router(users.router)
router.include_router(teams.router)

__all__ = ["router"]
