"""Team management endpoints for creating, listing, updating, and deleting teams."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    TeamAlreadyExistsException,
    TeamNotFoundException,
    TeamUpdateConflictException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import teams as teams_logic
from ...schemas.team import TeamCreate, TeamDetail, TeamList, TeamUpdate
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamDetail, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamDetail:
    """Create a new team."""
    user_id = UUID(token_data.sub)

    try:
        team = await teams_logic.create_team(
            team_data=team_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return TeamDetail.model_validate(team)
    except TeamAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=TeamList)
async def list_teams(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamList:
    """List all teams in the given organization."""
    user_id = UUID(token_data.sub)

    try:
        teams = await teams_logic.list_teams(org_id=org_id, user_id=user_id, db=db)
        return TeamList(teams=[TeamDetail.model_validate(team) for team in teams])
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamDetail:
    """Get a single team by ID."""
    user_id = UUID(token_data.sub)

    try:
        team = await teams_logic.get_team(
            team_id=team_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return TeamDetail.model_validate(team)
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{team_id}", response_model=TeamDetail)
async def update_team(
    team_id: UUID,
    team_data: TeamUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamDetail:
    """Update a team."""
    user_id = UUID(token_data.sub)

    try:
        team = await teams_logic.update_team(
            team_id=team_id,
            team_data=team_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return TeamDetail.model_validate(team)
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TeamUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[bool, Query(description="Hard delete the team")] = False,
) -> None:
    """Delete a team (cascades to team members)."""
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
        await teams_logic.delete_team(
            team_id=team_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
