"""Business logic for sprint management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    SprintNotFoundException,
    SprintUpdateConflictException,
)
from ...models import KSprint
from ...schemas.sprint import SprintCreate, SprintUpdate
from ..deps import verify_organization_membership


async def create_sprint(
    sprint_data: SprintCreate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KSprint:
    """Create a new sprint.

    Args:
        sprint_data: Sprint creation data
        user_id: ID of the user creating the sprint
        org_id: Organization ID for the sprint
        db: Database session

    Returns:
        The created sprint model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Create new sprint with audit fields
    new_sprint = KSprint(
        title=sprint_data.title,
        status=sprint_data.status,
        end_ts=sprint_data.end_ts,
        org_id=org_id,
        meta=sprint_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_sprint)

    try:
        await db.commit()
        await db.refresh(new_sprint)
    except IntegrityError as e:
        await db.rollback()
        raise SprintUpdateConflictException(
            sprint_id=new_sprint.id, scope=str(org_id)
        ) from e

    return new_sprint


async def list_sprints(org_id: UUID, user_id: UUID, db: AsyncSession) -> list[KSprint]:
    """List all sprints in the given organization.

    Args:
        org_id: Organization ID to filter sprints by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of sprint models

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KSprint).where(KSprint.org_id == org_id, KSprint.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    sprints = result.scalars().all()
    return list(sprints)


async def get_sprint(
    sprint_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> KSprint:
    """Get a single sprint by ID.

    Args:
        sprint_id: ID of the sprint to retrieve
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The sprint model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        SprintNotFoundException: If the sprint is not found in the given organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.org_id == org_id, KSprint.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=str(org_id))

    return sprint


async def update_sprint(
    sprint_id: UUID,
    sprint_data: SprintUpdate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KSprint:
    """Update a sprint.

    Args:
        sprint_id: ID of the sprint to update
        sprint_data: Sprint update data
        user_id: ID of the user performing the update
        org_id: Organization ID to filter by
        db: Database session

    Returns:
        The updated sprint model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        SprintNotFoundException: If the sprint is not found
        SprintUpdateConflictException: If updating causes a conflict
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.org_id == org_id, KSprint.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=str(org_id))

    # Update only provided fields
    if sprint_data.title is not None:
        sprint.title = sprint_data.title
    if sprint_data.status is not None:
        sprint.status = sprint_data.status
    if sprint_data.end_ts is not None:
        sprint.end_ts = sprint_data.end_ts
    if sprint_data.meta is not None:
        sprint.meta = sprint_data.meta

    # Update audit fields
    sprint.last_modified = datetime.now()
    sprint.last_modified_by = user_id

    try:
        await db.commit()
        await db.refresh(sprint)
    except IntegrityError as e:
        await db.rollback()
        raise SprintUpdateConflictException(
            sprint_id=sprint_id,
            scope=str(org_id),
        ) from e

    return sprint


async def delete_sprint(
    sprint_id: UUID,
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Delete a sprint.

    Args:
        sprint_id: ID of the sprint to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the sprint. If False, soft delete.

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        SprintNotFoundException: If the sprint is not found
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.org_id == org_id, KSprint.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=str(org_id))

    if hard_delete:  # pragma: no cover
        await db.delete(sprint)  # pragma: no cover
    else:
        sprint.deleted_at = datetime.now()
        sprint.last_modified = datetime.now()
        sprint.last_modified_by = user_id
    await db.commit()
