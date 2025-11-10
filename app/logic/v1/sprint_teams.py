"""Business logic for sprint team management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    SprintNotFoundException,
    SprintTeamAlreadyExistsException,
    SprintTeamNotFoundException,
    TeamNotFoundException,
)
from ...models import KSprint, KSprintTeam, KTeam
from ...schemas.sprint_team import SprintTeamCreate, SprintTeamUpdate


async def add_sprint_team(
    sprint_id: UUID,
    team_data: SprintTeamCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KSprintTeam:
    """Add a new team to a sprint.

    Args:
        sprint_id: ID of the sprint
        team_data: Sprint team creation data
        user_id: ID of the user adding the team
        db: Database session

    Returns:
        The created sprint team model

    Raises:
        SprintNotFoundException: If the sprint is not found
        TeamNotFoundException: If the team is not found
        SprintTeamAlreadyExistsException: If the team already exists in the sprint
    """
    # Verify sprint exists and get its org_id
    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = sprint.org_id

    # Verify team exists and belongs to the same org
    team_stmt = select(KTeam).where(
        KTeam.id == team_data.team_id,  # type: ignore[arg-type]
        KTeam.org_id == org_id,  # type: ignore[arg-type]
        KTeam.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(team_stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_data.team_id, scope=str(org_id))

    # Create new sprint team with audit fields
    new_sprint_team = KSprintTeam(
        sprint_id=sprint_id,
        team_id=team_data.team_id,
        org_id=org_id,
        role=team_data.role,
        meta=team_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_sprint_team)

    try:
        await db.commit()
        await db.refresh(new_sprint_team)
    except IntegrityError as e:
        await db.rollback()
        raise SprintTeamAlreadyExistsException(
            sprint_id=sprint_id, team_id=team_data.team_id, scope=str(org_id)
        ) from e

    return new_sprint_team


async def list_sprint_teams(sprint_id: UUID, db: AsyncSession) -> list[KSprintTeam]:
    """List all teams of a sprint.

    Args:
        sprint_id: ID of the sprint
        db: Database session

    Returns:
        List of sprint team models

    Raises:
        SprintNotFoundException: If the sprint is not found
    """
    # Verify sprint exists
    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=None)

    # Get all teams for this sprint
    stmt = select(KSprintTeam).where(  # type: ignore[assignment]
        KSprintTeam.sprint_id == sprint_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    teams = result.scalars().all()
    return list(teams)  # type: ignore[arg-type]


async def get_sprint_team(
    sprint_id: UUID, team_id: UUID, db: AsyncSession
) -> KSprintTeam:
    """Get a single sprint team.

    Args:
        sprint_id: ID of the sprint
        team_id: ID of the team
        db: Database session

    Returns:
        The sprint team model

    Raises:
        SprintTeamNotFoundException: If the sprint team is not found
    """
    stmt = select(KSprintTeam).where(
        KSprintTeam.sprint_id == sprint_id,  # type: ignore[arg-type]
        KSprintTeam.team_id == team_id,  # type: ignore[arg-type]
        KSprintTeam.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    sprint_team = result.scalar_one_or_none()

    if not sprint_team:
        raise SprintTeamNotFoundException(
            sprint_id=sprint_id, team_id=team_id, scope=None
        )

    return sprint_team


async def update_sprint_team(
    sprint_id: UUID,
    team_id: UUID,
    team_data: SprintTeamUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KSprintTeam:
    """Update a sprint team.

    Args:
        sprint_id: ID of the sprint
        team_id: ID of the team
        team_data: Sprint team update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated sprint team model

    Raises:
        SprintTeamNotFoundException: If the sprint team is not found
    """
    stmt = select(KSprintTeam).where(
        KSprintTeam.sprint_id == sprint_id,  # type: ignore[arg-type]
        KSprintTeam.team_id == team_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    sprint_team = result.scalar_one_or_none()

    if not sprint_team:
        raise SprintTeamNotFoundException(
            sprint_id=sprint_id, team_id=team_id, scope=None
        )

    # Update only provided fields
    if team_data.role is not None:
        sprint_team.role = team_data.role
    if team_data.meta is not None:
        sprint_team.meta = team_data.meta

    # Update audit fields
    sprint_team.last_modified = datetime.now()
    sprint_team.last_modified_by = user_id

    await db.commit()
    await db.refresh(sprint_team)

    return sprint_team


async def remove_sprint_team(
    sprint_id: UUID,
    team_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Remove a team from a sprint.

    Args:
        sprint_id: ID of the sprint
        team_id: ID of the team
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the relationship. If False, soft delete.

    Raises:
        SprintTeamNotFoundException: If the sprint team is not found
    """
    stmt = select(KSprintTeam).where(
        KSprintTeam.sprint_id == sprint_id,  # type: ignore[arg-type]
        KSprintTeam.team_id == team_id,  # type: ignore[arg-type]
        KSprintTeam.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    sprint_team = result.scalar_one_or_none()

    if not sprint_team:
        raise SprintTeamNotFoundException(
            sprint_id=sprint_id, team_id=team_id, scope=None
        )

    if hard_delete:  # pragma: no cover
        await db.delete(sprint_team)  # pragma: no cover
    else:
        sprint_team.deleted_at = datetime.now()
        sprint_team.last_modified = datetime.now()
        sprint_team.last_modified_by = user_id
    await db.commit()
