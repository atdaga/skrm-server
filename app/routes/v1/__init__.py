"""V1 API router aggregating all v1 endpoints."""

from fastapi import APIRouter

from . import (
    deployment_envs,
    docs,
    feature_docs,
    features,
    organization_principals,
    organizations,
    project_teams,
    projects,
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
router.include_router(projects.router)
router.include_router(project_teams.router)
router.include_router(deployment_envs.router)
router.include_router(docs.router)
router.include_router(features.router)
router.include_router(feature_docs.router)

__all__ = ["router"]
