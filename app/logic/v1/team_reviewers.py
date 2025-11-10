"""Business logic for team reviewer management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    TeamNotFoundException,
    TeamReviewerAlreadyExistsException,
    TeamReviewerNotFoundException,
)
from ...models import KTeam, KTeamReviewer
from ...schemas.team_reviewer import TeamReviewerCreate, TeamReviewerUpdate


async def add_team_reviewer(
    team_id: UUID,
    reviewer_data: TeamReviewerCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KTeamReviewer:
    """Add a new reviewer to a team.

    Args:
        team_id: ID of the team
        reviewer_data: Team reviewer creation data
        user_id: ID of the user adding the reviewer
        db: Database session

    Returns:
        The created team reviewer model

    Raises:
        TeamNotFoundException: If the team is not found
        TeamReviewerAlreadyExistsException: If the reviewer already exists in the team
    """
    # Verify team exists and get its org_id
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = team.org_id

    # Create new team reviewer with audit fields
    new_reviewer = KTeamReviewer(
        team_id=team_id,
        principal_id=reviewer_data.principal_id,
        org_id=org_id,
        role=reviewer_data.role,
        meta=reviewer_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_reviewer)

    try:
        await db.commit()
        await db.refresh(new_reviewer)
    except IntegrityError as e:
        await db.rollback()
        raise TeamReviewerAlreadyExistsException(
            team_id=team_id, principal_id=reviewer_data.principal_id, scope=str(org_id)
        ) from e

    return new_reviewer


async def list_team_reviewers(team_id: UUID, db: AsyncSession) -> list[KTeamReviewer]:
    """List all reviewers of a team.

    Args:
        team_id: ID of the team
        db: Database session

    Returns:
        List of team reviewer models

    Raises:
        TeamNotFoundException: If the team is not found
    """
    # Verify team exists and get its org_id
    stmt = select(KTeam).where(KTeam.id == team_id, KTeam.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise TeamNotFoundException(team_id=team_id, scope=None)

    # Get all reviewers for this team
    stmt = select(KTeamReviewer).where(  # type: ignore[assignment]
        KTeamReviewer.team_id == team_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    reviewers = result.scalars().all()
    return list(reviewers)  # type: ignore[arg-type]


async def get_team_reviewer(
    team_id: UUID, principal_id: UUID, db: AsyncSession
) -> KTeamReviewer:
    """Get a single team reviewer.

    Args:
        team_id: ID of the team
        principal_id: ID of the principal (reviewer)
        db: Database session

    Returns:
        The team reviewer model

    Raises:
        TeamReviewerNotFoundException: If the team reviewer is not found
    """
    stmt = select(KTeamReviewer).where(
        KTeamReviewer.team_id == team_id,  # type: ignore[arg-type]
        KTeamReviewer.principal_id == principal_id,  # type: ignore[arg-type]
        KTeamReviewer.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    reviewer = result.scalar_one_or_none()

    if not reviewer:
        raise TeamReviewerNotFoundException(
            team_id=team_id, principal_id=principal_id, scope=None
        )

    return reviewer


async def update_team_reviewer(
    team_id: UUID,
    principal_id: UUID,
    reviewer_data: TeamReviewerUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KTeamReviewer:
    """Update a team reviewer.

    Args:
        team_id: ID of the team
        principal_id: ID of the principal (reviewer)
        reviewer_data: Team reviewer update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated team reviewer model

    Raises:
        TeamReviewerNotFoundException: If the team reviewer is not found
    """
    stmt = select(KTeamReviewer).where(
        KTeamReviewer.team_id == team_id,  # type: ignore[arg-type]
        KTeamReviewer.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    reviewer = result.scalar_one_or_none()

    if not reviewer:
        raise TeamReviewerNotFoundException(
            team_id=team_id, principal_id=principal_id, scope=None
        )

    # Update only provided fields
    if reviewer_data.role is not None:
        reviewer.role = reviewer_data.role
    if reviewer_data.meta is not None:
        reviewer.meta = reviewer_data.meta

    # Update audit fields
    reviewer.last_modified = datetime.now()
    reviewer.last_modified_by = user_id

    await db.commit()
    await db.refresh(reviewer)

    return reviewer


async def remove_team_reviewer(
    team_id: UUID,
    principal_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Remove a reviewer from a team.

    Args:
        team_id: ID of the team
        principal_id: ID of the principal (reviewer)
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the relationship. If False, soft delete.

    Raises:
        TeamReviewerNotFoundException: If the team reviewer is not found
    """
    stmt = select(KTeamReviewer).where(
        KTeamReviewer.team_id == team_id,  # type: ignore[arg-type]
        KTeamReviewer.principal_id == principal_id,  # type: ignore[arg-type]
        KTeamReviewer.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    reviewer = result.scalar_one_or_none()

    if not reviewer:
        raise TeamReviewerNotFoundException(
            team_id=team_id, principal_id=principal_id, scope=None
        )

    if hard_delete:  # pragma: no cover
        await db.delete(reviewer)  # pragma: no cover
    else:
        reviewer.deleted_at = datetime.now()
        reviewer.last_modified = datetime.now()
        reviewer.last_modified_by = user_id
    await db.commit()
