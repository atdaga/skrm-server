"""Team management endpoints for creating, listing, updating, and deleting teams."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_current_token
from ...core.db.database import get_db
from ...models import KTeam
from ...schemas.team import TeamCreate, TeamUpdate, TeamDetail
from ...schemas.user import TokenData

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamDetail, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamDetail:
    """Create a new team."""
    # Create new team with audit fields
    new_team = KTeam(
        name=team_data.name,
        scope=token_data.scope,
        meta=team_data.meta,
        created_by=token_data.sub,
        last_modified_by=token_data.sub,
    )

    db.add(new_team)

    try:
        await db.commit()
        await db.refresh(new_team)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team with name '{team_data.name}' already exists in scope '{team_data.scope}'",
        )

    return TeamDetail.model_validate(new_team)


@router.get("", response_model=list[TeamDetail])
async def list_teams(
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TeamDetail]:
    """List all teams in the current user's scope."""
    stmt = select(KTeam).where(KTeam.scope == token_data.scope)
    result = await db.execute(stmt)
    teams = result.scalars().all()

    return [TeamDetail.model_validate(team) for team in teams]


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamDetail:
    """Get a single team by ID."""
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == token_data.scope)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id '{team_id}' not found",
        )

    return TeamDetail.model_validate(team)


@router.patch("/{team_id}", response_model=TeamDetail)
async def update_team(
    team_id: UUID,
    team_data: TeamUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamDetail:
    """Update a team."""
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == token_data.scope)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id '{team_id}' not found",
        )

    # Update only provided fields
    if team_data.name is not None:
        team.name = team_data.name
    if team_data.meta is not None:
        team.meta = team_data.meta

    # Update audit fields
    team.last_modified = datetime.now()
    team.last_modified_by = token_data.sub

    try:
        await db.commit()
        await db.refresh(team)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team with name '{team_data.name}' already exists in scope '{team.scope}'",
        )

    return TeamDetail.model_validate(team)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a team (cascades to team members)."""
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == token_data.scope)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id '{team_id}' not found",
        )

    await db.delete(team)
    await db.commit()
