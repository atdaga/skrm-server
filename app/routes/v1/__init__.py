"""V1 API router aggregating all v1 endpoints."""

from fastapi import APIRouter

from . import (
    organization_principals,
    organizations,
    team_members,
    team_reviewers,
    teams,
    users,
)

# Create main v1 router
router = APIRouter()

# Include all v1 subrouters
router.include_router(users.router)
router.include_router(organizations.router)
router.include_router(organization_principals.router)
router.include_router(teams.router)
router.include_router(team_members.router)
router.include_router(team_reviewers.router)

__all__ = ["router"]
