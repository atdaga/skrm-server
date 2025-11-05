"""Business logic for team member management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    TeamMemberAlreadyExistsException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
)
from ...models import KTeam, KTeamMember
from ...schemas.team_member import TeamMemberCreate, TeamMemberUpdate


async def add_team_member(
    team_id: UUID,
    member_data: TeamMemberCreate,
    user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KTeamMember:
    """Add a new member to a team.

    Args:
        team_id: ID of the team
        member_data: Team member creation data
        user_id: ID of the user adding the member
        scope: Scope for the team member
        db: Database session

    Returns:
        The created team member model

    Raises:
        TeamNotFoundException: If the team is not found
        TeamMemberAlreadyExistsException: If the member already exists in the team
    """
    # Verify team exists in scope
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == scope)  # type: ignore
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=scope)

    # Create new team member with audit fields
    new_member = KTeamMember(
        team_id=team_id,
        principal_id=member_data.principal_id,
        scope=scope,
        role=member_data.role,
        meta=member_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_member)

    try:
        await db.commit()
        await db.refresh(new_member)
    except IntegrityError as e:
        await db.rollback()
        raise TeamMemberAlreadyExistsException(
            team_id=team_id, principal_id=member_data.principal_id, scope=scope
        ) from e

    return new_member


async def list_team_members(
    team_id: UUID, scope: str, db: AsyncSession
) -> list[KTeamMember]:
    """List all members of a team.

    Args:
        team_id: ID of the team
        scope: Scope to filter by
        db: Database session

    Returns:
        List of team member models

    Raises:
        TeamNotFoundException: If the team is not found
    """
    # Verify team exists in scope
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.scope == scope)  # type: ignore
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=scope)

    # Get all members for this team in the scope
    stmt = select(KTeamMember).where(
        KTeamMember.team_id == team_id, KTeamMember.scope == scope  # type: ignore
    )
    result = await db.execute(stmt)
    members = result.scalars().all()
    return list(members)


async def get_team_member(
    team_id: UUID, principal_id: UUID, scope: str, db: AsyncSession
) -> KTeamMember:
    """Get a single team member.

    Args:
        team_id: ID of the team
        principal_id: ID of the principal (member)
        scope: Scope to filter by
        db: Database session

    Returns:
        The team member model

    Raises:
        TeamMemberNotFoundException: If the team member is not found
    """
    stmt = select(KTeamMember).where(
        KTeamMember.team_id == team_id,
        KTeamMember.principal_id == principal_id,
        KTeamMember.scope == scope,  # type: ignore
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise TeamMemberNotFoundException(
            team_id=team_id, principal_id=principal_id, scope=scope
        )

    return member


async def update_team_member(
    team_id: UUID,
    principal_id: UUID,
    member_data: TeamMemberUpdate,
    user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KTeamMember:
    """Update a team member.

    Args:
        team_id: ID of the team
        principal_id: ID of the principal (member)
        member_data: Team member update data
        user_id: ID of the user performing the update
        scope: Scope to filter by
        db: Database session

    Returns:
        The updated team member model

    Raises:
        TeamMemberNotFoundException: If the team member is not found
    """
    stmt = select(KTeamMember).where(
        KTeamMember.team_id == team_id,
        KTeamMember.principal_id == principal_id,
        KTeamMember.scope == scope,  # type: ignore
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise TeamMemberNotFoundException(
            team_id=team_id, principal_id=principal_id, scope=scope
        )

    # Update only provided fields
    if member_data.role is not None:
        member.role = member_data.role
    if member_data.meta is not None:
        member.meta = member_data.meta

    # Update audit fields
    member.last_modified = datetime.now()
    member.last_modified_by = user_id

    await db.commit()
    await db.refresh(member)

    return member


async def remove_team_member(
    team_id: UUID, principal_id: UUID, scope: str, db: AsyncSession
) -> None:
    """Remove a member from a team.

    Args:
        team_id: ID of the team
        principal_id: ID of the principal (member)
        scope: Scope to filter by
        db: Database session

    Raises:
        TeamMemberNotFoundException: If the team member is not found
    """
    stmt = select(KTeamMember).where(
        KTeamMember.team_id == team_id,
        KTeamMember.principal_id == principal_id,
        KTeamMember.scope == scope,  # type: ignore
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise TeamMemberNotFoundException(
            team_id=team_id, principal_id=principal_id, scope=scope
        )

    await db.delete(member)
    await db.commit()
