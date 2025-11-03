"""Business logic for team management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    TeamAlreadyExistsException,
    TeamNotFoundException,
    TeamUpdateConflictException,
)
from ...models import KTeam
from ...schemas.team import TeamCreate, TeamUpdate


async def create_team(
    team_data: TeamCreate,
    user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KTeam:
    """Create a new team.
    
    Args:
        team_data: Team creation data
        user_id: ID of the user creating the team
        scope: Scope for the team
        db: Database session
        
    Returns:
        The created team model
        
    Raises:
        TeamAlreadyExistsException: If a team with the same name already exists in the scope
    """
    # Create new team with audit fields
    new_team = KTeam(
        name=team_data.name,
        scope=scope,
        meta=team_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_team)

    try:
        await db.commit()
        await db.refresh(new_team)
    except IntegrityError as e:
        await db.rollback()
        raise TeamAlreadyExistsException(name=team_data.name, scope=scope) from e

    return new_team


async def list_teams(scope: str, db: AsyncSession) -> list[KTeam]:
    """List all teams in the given scope.
    
    Args:
        scope: Scope to filter teams by
        db: Database session
        
    Returns:
        List of team models
    """
    stmt = select(KTeam).where(KTeam.scope == scope)  # type: ignore
    result = await db.execute(stmt)
    teams = result.scalars().all()
    return list(teams)


async def get_team(team_id: UUID, scope: str, db: AsyncSession) -> KTeam:
    """Get a single team by ID.
    
    Args:
        team_id: ID of the team to retrieve
        scope: Scope to filter by
        db: Database session
        
    Returns:
        The team model
        
    Raises:
        TeamNotFoundException: If the team is not found in the given scope
    """
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == scope)  # type: ignore
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=scope)

    return team


async def update_team(
    team_id: UUID,
    team_data: TeamUpdate,
    user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KTeam:
    """Update a team.
    
    Args:
        team_id: ID of the team to update
        team_data: Team update data
        user_id: ID of the user performing the update
        scope: Scope to filter by
        db: Database session
        
    Returns:
        The updated team model
        
    Raises:
        TeamNotFoundException: If the team is not found
        TeamUpdateConflictException: If updating causes a name conflict
    """
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == scope)  # type: ignore
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=scope)

    # Update only provided fields
    if team_data.name is not None:
        team.name = team_data.name
    if team_data.meta is not None:
        team.meta = team_data.meta

    # Update audit fields
    team.last_modified = datetime.now()
    team.last_modified_by = user_id

    try:
        await db.commit()
        await db.refresh(team)
    except IntegrityError as e:
        await db.rollback()
        raise TeamUpdateConflictException(
            team_id=team_id,
            name=team_data.name or team.name,
            scope=scope,
        ) from e

    return team


async def delete_team(team_id: UUID, scope: str, db: AsyncSession) -> None:
    """Delete a team.
    
    Args:
        team_id: ID of the team to delete
        scope: Scope to filter by
        db: Database session
        
    Raises:
        TeamNotFoundException: If the team is not found
    """
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == scope)  # type: ignore
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=scope)

    await db.delete(team)
    await db.commit()

