"""Business logic for sprint task management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    SprintNotFoundException,
    SprintTaskAlreadyExistsException,
    SprintTaskNotFoundException,
    TaskNotFoundException,
)
from ...models import KSprint, KSprintTask, KTask
from ...schemas.sprint_task import SprintTaskCreate, SprintTaskUpdate


async def add_sprint_task(
    sprint_id: UUID,
    task_data: SprintTaskCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KSprintTask:
    """Add a new task to a sprint.

    Args:
        sprint_id: ID of the sprint
        task_data: Sprint task creation data
        user_id: ID of the user adding the task
        db: Database session

    Returns:
        The created sprint task model

    Raises:
        SprintNotFoundException: If the sprint is not found
        TaskNotFoundException: If the task is not found
        SprintTaskAlreadyExistsException: If the task already exists in the sprint
    """
    # Verify sprint exists and get its org_id
    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = sprint.org_id

    # Verify task exists and belongs to the same org
    task_stmt = select(KTask).where(
        KTask.id == task_data.task_id,  # type: ignore[arg-type]
        KTask.org_id == org_id,  # type: ignore[arg-type]
        KTask.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(task_stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_data.task_id, scope=str(org_id))

    # Create new sprint task with audit fields
    new_sprint_task = KSprintTask(
        sprint_id=sprint_id,
        task_id=task_data.task_id,
        org_id=org_id,
        role=task_data.role,
        meta=task_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_sprint_task)

    try:
        await db.commit()
        await db.refresh(new_sprint_task)
    except IntegrityError as e:
        await db.rollback()
        raise SprintTaskAlreadyExistsException(
            sprint_id=sprint_id, task_id=task_data.task_id, scope=str(org_id)
        ) from e

    return new_sprint_task


async def list_sprint_tasks(sprint_id: UUID, db: AsyncSession) -> list[KSprintTask]:
    """List all tasks of a sprint.

    Args:
        sprint_id: ID of the sprint
        db: Database session

    Returns:
        List of sprint task models

    Raises:
        SprintNotFoundException: If the sprint is not found
    """
    # Verify sprint exists
    stmt = select(KSprint).where(KSprint.id == sprint_id, KSprint.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    sprint = result.scalar_one_or_none()

    if not sprint:
        raise SprintNotFoundException(sprint_id=sprint_id, scope=None)

    # Get all tasks for this sprint
    stmt = select(KSprintTask).where(  # type: ignore[assignment]
        KSprintTask.sprint_id == sprint_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return list(tasks)  # type: ignore[arg-type]


async def get_sprint_task(
    sprint_id: UUID, task_id: UUID, db: AsyncSession
) -> KSprintTask:
    """Get a single sprint task.

    Args:
        sprint_id: ID of the sprint
        task_id: ID of the task
        db: Database session

    Returns:
        The sprint task model

    Raises:
        SprintTaskNotFoundException: If the sprint task is not found
    """
    stmt = select(KSprintTask).where(
        KSprintTask.sprint_id == sprint_id,  # type: ignore[arg-type]
        KSprintTask.task_id == task_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    sprint_task = result.scalar_one_or_none()

    if not sprint_task:
        raise SprintTaskNotFoundException(
            sprint_id=sprint_id, task_id=task_id, scope=None
        )

    return sprint_task


async def update_sprint_task(
    sprint_id: UUID,
    task_id: UUID,
    task_data: SprintTaskUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KSprintTask:
    """Update a sprint task.

    Args:
        sprint_id: ID of the sprint
        task_id: ID of the task
        task_data: Sprint task update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated sprint task model

    Raises:
        SprintTaskNotFoundException: If the sprint task is not found
    """
    stmt = select(KSprintTask).where(
        KSprintTask.sprint_id == sprint_id,  # type: ignore[arg-type]
        KSprintTask.task_id == task_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    sprint_task = result.scalar_one_or_none()

    if not sprint_task:
        raise SprintTaskNotFoundException(
            sprint_id=sprint_id, task_id=task_id, scope=None
        )

    # Update only provided fields
    if task_data.role is not None:
        sprint_task.role = task_data.role
    if task_data.meta is not None:
        sprint_task.meta = task_data.meta

    # Update audit fields
    sprint_task.last_modified = datetime.now()
    sprint_task.last_modified_by = user_id

    await db.commit()
    await db.refresh(sprint_task)

    return sprint_task


async def remove_sprint_task(sprint_id: UUID, task_id: UUID, db: AsyncSession) -> None:
    """Remove a task from a sprint.

    Args:
        sprint_id: ID of the sprint
        task_id: ID of the task
        db: Database session

    Raises:
        SprintTaskNotFoundException: If the sprint task is not found
    """
    stmt = select(KSprintTask).where(
        KSprintTask.sprint_id == sprint_id,  # type: ignore[arg-type]
        KSprintTask.task_id == task_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    sprint_task = result.scalar_one_or_none()

    if not sprint_task:
        raise SprintTaskNotFoundException(
            sprint_id=sprint_id, task_id=task_id, scope=None
        )

    await db.delete(sprint_task)
    await db.commit()
