"""Project team management endpoints for adding, listing, updating, and removing project teams."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    ProjectNotFoundException,
    ProjectTeamAlreadyExistsException,
    ProjectTeamNotFoundException,
)
from ...logic.v1 import project_teams as project_teams_logic
from ...schemas.project_team import (
    ProjectTeamCreate,
    ProjectTeamDetail,
    ProjectTeamList,
    ProjectTeamUpdate,
)
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/projects/{project_id}/teams", tags=["project-teams"])


@router.post("", response_model=ProjectTeamDetail, status_code=status.HTTP_201_CREATED)
async def add_project_team(
    project_id: UUID,
    team_data: ProjectTeamCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectTeamDetail:
    """Add a new team to a project."""
    user_id = UUID(token_data.sub)

    try:
        team = await project_teams_logic.add_project_team(
            project_id=project_id,
            team_data=team_data,
            user_id=user_id,
            db=db,
        )
        return ProjectTeamDetail.model_validate(team)
    except ProjectNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except ProjectTeamAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=ProjectTeamList)
async def list_project_teams(
    project_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectTeamList:
    """List all teams of a project."""
    try:
        teams = await project_teams_logic.list_project_teams(
            project_id=project_id, db=db
        )
        return ProjectTeamList(
            teams=[ProjectTeamDetail.model_validate(team) for team in teams]
        )
    except ProjectNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{team_id}", response_model=ProjectTeamDetail)
async def get_project_team(
    project_id: UUID,
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectTeamDetail:
    """Get a single project team."""
    try:
        team = await project_teams_logic.get_project_team(
            project_id=project_id,
            team_id=team_id,
            db=db,
        )
        return ProjectTeamDetail.model_validate(team)
    except ProjectTeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{team_id}", response_model=ProjectTeamDetail)
async def update_project_team(
    project_id: UUID,
    team_id: UUID,
    team_data: ProjectTeamUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectTeamDetail:
    """Update a project team."""
    user_id = UUID(token_data.sub)

    try:
        team = await project_teams_logic.update_project_team(
            project_id=project_id,
            team_id=team_id,
            team_data=team_data,
            user_id=user_id,
            db=db,
        )
        return ProjectTeamDetail.model_validate(team)
    except ProjectTeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_team(
    project_id: UUID,
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a team from a project."""
    try:
        await project_teams_logic.remove_project_team(
            project_id=project_id,
            team_id=team_id,
            db=db,
        )
    except ProjectTeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
