"""Business logic for task management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import TaskNotFoundException
from ...models import KTask
from ...schemas.task import TaskCreate, TaskUpdate
from ..deps import verify_organization_membership


async def create_task(
    task_data: TaskCreate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KTask:
    """Create a new task.

    Args:
        task_data: Task creation data
        user_id: ID of the user creating the task
        org_id: Organization ID for the task
        db: Database session

    Returns:
        The created task model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Create new task with audit fields
    new_task = KTask(
        org_id=org_id,
        summary=task_data.summary,
        description=task_data.description,
        team_id=task_data.team_id,
        guestimate=task_data.guestimate,
        status=task_data.status,
        review_result=task_data.review_result,
        meta=task_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_task)
    if in_transaction:  # pragma: no cover - tested via txs integration
        # Already in a transaction (managed by txs), just flush
        await db.flush()  # pragma: no cover
    else:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
    await db.refresh(new_task)

    return new_task


async def list_tasks(org_id: UUID, user_id: UUID, db: AsyncSession) -> list[KTask]:
    """List all tasks in the given organization.

    Args:
        org_id: Organization ID to filter tasks by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of task models

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KTask).where(KTask.org_id == org_id, KTask.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return list(tasks)


async def get_task(
    task_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> KTask:
    """Get a single task by ID.

    Args:
        task_id: ID of the task to retrieve
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The task model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        TaskNotFoundException: If the task is not found in the given organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KTask).where(KTask.id == task_id, KTask.org_id == org_id, KTask.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=str(org_id))

    return task


async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KTask:
    """Update a task.

    Args:
        task_id: ID of the task to update
        task_data: Task update data
        user_id: ID of the user performing the update
        org_id: Organization ID to filter by
        db: Database session

    Returns:
        The updated task model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        TaskNotFoundException: If the task is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KTask).where(KTask.id == task_id, KTask.org_id == org_id, KTask.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=str(org_id))

    # Update only provided fields
    if task_data.summary is not None:
        task.summary = task_data.summary
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.team_id is not None:
        task.team_id = task_data.team_id
    if task_data.guestimate is not None:
        task.guestimate = task_data.guestimate
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.review_result is not None:
        task.review_result = task_data.review_result
    if task_data.meta is not None:
        task.meta = task_data.meta

    # Update audit fields
    task.last_modified = datetime.now()
    task.last_modified_by = user_id

    if in_transaction:  # pragma: no cover - tested via txs integration
        # Already in a transaction (managed by txs), just flush
        await db.flush()  # pragma: no cover
    else:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
    await db.refresh(task)

    return task


async def delete_task(
    task_id: UUID,
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Delete a task.

    Args:
        task_id: ID of the task to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the task. If False, soft delete.

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        TaskNotFoundException: If the task is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KTask).where(KTask.id == task_id, KTask.org_id == org_id, KTask.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=str(org_id))

    if hard_delete:  # pragma: no cover
        await db.delete(task)  # pragma: no cover
    else:
        task.deleted_at = datetime.now()
        task.last_modified = datetime.now()
        task.last_modified_by = user_id
    if not in_transaction:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
