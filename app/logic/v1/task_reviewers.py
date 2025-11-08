"""Business logic for task reviewer management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    PrincipalNotFoundException,
    TaskNotFoundException,
    TaskReviewerAlreadyExistsException,
    TaskReviewerNotFoundException,
)
from ...models import KOrganizationPrincipal, KTask, KTaskReviewer
from ...schemas.task_reviewer import TaskReviewerCreate, TaskReviewerUpdate


async def add_task_reviewer(
    task_id: UUID,
    reviewer_data: TaskReviewerCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskReviewer:
    """Add a new reviewer to a task.

    Args:
        task_id: ID of the task
        reviewer_data: Task reviewer creation data
        user_id: ID of the user adding the reviewer
        db: Database session

    Returns:
        The created task reviewer model

    Raises:
        TaskNotFoundException: If the task is not found
        PrincipalNotFoundException: If the principal is not found
        TaskReviewerAlreadyExistsException: If the reviewer already exists for the task
    """
    # Verify task exists and get its org_id
    stmt = select(KTask).where(KTask.id == task_id, KTask.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = task.org_id

    # Verify principal exists and belongs to the same org
    principal_stmt = select(KOrganizationPrincipal).where(
        KOrganizationPrincipal.principal_id == reviewer_data.principal_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.org_id == org_id,  # type: ignore[arg-type]
    )
    result = await db.execute(principal_stmt)
    org_principal = result.scalar_one_or_none()

    if not org_principal:
        raise PrincipalNotFoundException(
            principal_id=reviewer_data.principal_id, scope=str(org_id)
        )

    # Create new task reviewer with audit fields
    new_task_reviewer = KTaskReviewer(
        task_id=task_id,
        principal_id=reviewer_data.principal_id,
        org_id=org_id,
        role=reviewer_data.role,
        meta=reviewer_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_task_reviewer)

    try:
        await db.commit()
        await db.refresh(new_task_reviewer)
    except IntegrityError as e:
        await db.rollback()
        raise TaskReviewerAlreadyExistsException(
            task_id=task_id,
            principal_id=reviewer_data.principal_id,
            scope=str(org_id),
        ) from e

    return new_task_reviewer


async def list_task_reviewers(task_id: UUID, db: AsyncSession) -> list[KTaskReviewer]:
    """List all reviewers for a task.

    Args:
        task_id: ID of the task
        db: Database session

    Returns:
        List of task reviewer models

    Raises:
        TaskNotFoundException: If the task is not found
    """
    # Verify task exists
    stmt = select(KTask).where(KTask.id == task_id, KTask.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Get all reviewers for this task
    stmt = select(KTaskReviewer).where(  # type: ignore[assignment]
        KTaskReviewer.task_id == task_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    reviewers = result.scalars().all()
    return list(reviewers)  # type: ignore[arg-type]


async def get_task_reviewer(
    task_id: UUID, principal_id: UUID, db: AsyncSession
) -> KTaskReviewer:
    """Get a single task reviewer relationship.

    Args:
        task_id: ID of the task
        principal_id: ID of the principal
        db: Database session

    Returns:
        The task reviewer model

    Raises:
        TaskReviewerNotFoundException: If the task reviewer relationship is not found
    """
    stmt = select(KTaskReviewer).where(
        KTaskReviewer.task_id == task_id,  # type: ignore[arg-type]
        KTaskReviewer.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_reviewer = result.scalar_one_or_none()

    if not task_reviewer:
        raise TaskReviewerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope=None
        )

    return task_reviewer


async def update_task_reviewer(
    task_id: UUID,
    principal_id: UUID,
    reviewer_data: TaskReviewerUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskReviewer:
    """Update a task reviewer relationship.

    Args:
        task_id: ID of the task
        principal_id: ID of the principal
        reviewer_data: Task reviewer update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated task reviewer model

    Raises:
        TaskReviewerNotFoundException: If the task reviewer relationship is not found
    """
    stmt = select(KTaskReviewer).where(
        KTaskReviewer.task_id == task_id,  # type: ignore[arg-type]
        KTaskReviewer.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_reviewer = result.scalar_one_or_none()

    if not task_reviewer:
        raise TaskReviewerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope=None
        )

    # Update only provided fields
    if reviewer_data.role is not None:
        task_reviewer.role = reviewer_data.role
    if reviewer_data.meta is not None:
        task_reviewer.meta = reviewer_data.meta

    # Update audit fields
    task_reviewer.last_modified = datetime.now()
    task_reviewer.last_modified_by = user_id

    await db.commit()
    await db.refresh(task_reviewer)

    return task_reviewer


async def remove_task_reviewer(
    task_id: UUID, principal_id: UUID, db: AsyncSession
) -> None:
    """Remove a reviewer from a task.

    Args:
        task_id: ID of the task
        principal_id: ID of the principal
        db: Database session

    Raises:
        TaskReviewerNotFoundException: If the task reviewer relationship is not found
    """
    stmt = select(KTaskReviewer).where(
        KTaskReviewer.task_id == task_id,  # type: ignore[arg-type]
        KTaskReviewer.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_reviewer = result.scalar_one_or_none()

    if not task_reviewer:
        raise TaskReviewerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope=None
        )

    await db.delete(task_reviewer)
    await db.commit()
