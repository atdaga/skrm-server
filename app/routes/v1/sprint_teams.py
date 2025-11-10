"""Sprint team management endpoints for adding, listing, updating, and removing teams from sprints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    SprintNotFoundException,
    SprintTeamAlreadyExistsException,
    SprintTeamNotFoundException,
    TeamNotFoundException,
)
from ...logic.v1 import sprint_teams as sprint_teams_logic
from ...schemas.sprint_team import (
    SprintTeamCreate,
    SprintTeamDetail,
    SprintTeamList,
    SprintTeamUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/sprints/{sprint_id}/teams", tags=["sprint-teams"])


@router.post("", response_model=SprintTeamDetail, status_code=status.HTTP_201_CREATED)
async def add_sprint_team(
    sprint_id: UUID,
    team_data: SprintTeamCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTeamDetail:
    """Add a team to a sprint."""
    user_id = UUID(token_data.sub)

    try:
        sprint_team = await sprint_teams_logic.add_sprint_team(
            sprint_id=sprint_id,
            team_data=team_data,
            user_id=user_id,
            db=db,
        )
        return SprintTeamDetail.model_validate(sprint_team)
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except SprintTeamAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=SprintTeamList)
async def list_sprint_teams(
    sprint_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTeamList:
    """List all teams in a sprint."""
    try:
        teams = await sprint_teams_logic.list_sprint_teams(sprint_id=sprint_id, db=db)
        return SprintTeamList(
            teams=[SprintTeamDetail.model_validate(team) for team in teams]
        )
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{team_id}", response_model=SprintTeamDetail)
async def get_sprint_team(
    sprint_id: UUID,
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTeamDetail:
    """Get a single sprint team."""
    try:
        sprint_team = await sprint_teams_logic.get_sprint_team(
            sprint_id=sprint_id,
            team_id=team_id,
            db=db,
        )
        return SprintTeamDetail.model_validate(sprint_team)
    except SprintTeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{team_id}", response_model=SprintTeamDetail)
async def update_sprint_team(
    sprint_id: UUID,
    team_id: UUID,
    team_data: SprintTeamUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTeamDetail:
    """Update a sprint team."""
    user_id = UUID(token_data.sub)

    try:
        sprint_team = await sprint_teams_logic.update_sprint_team(
            sprint_id=sprint_id,
            team_id=team_id,
            team_data=team_data,
            user_id=user_id,
            db=db,
        )
        return SprintTeamDetail.model_validate(sprint_team)
    except SprintTeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_sprint_team(
    sprint_id: UUID,
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the relationship")
    ] = False,
) -> None:
    """Remove a team from a sprint."""
    user_id = UUID(token_data.sub)

    # Check authorization for hard delete
    if hard_delete:  # pragma: no cover
        from ...logic import deps as deps_logic  # pragma: no cover

        try:  # pragma: no cover
            deps_logic.check_hard_delete_privileges(current_user)  # pragma: no cover
        except InsufficientPrivilegesException as e:  # pragma: no cover
            raise HTTPException(  # pragma: no cover
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await sprint_teams_logic.remove_sprint_team(
            sprint_id=sprint_id,
            team_id=team_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except SprintTeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
