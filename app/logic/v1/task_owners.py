"""Business logic for task owner management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    PrincipalNotFoundException,
    TaskNotFoundException,
    TaskOwnerAlreadyExistsException,
    TaskOwnerNotFoundException,
)
from ...models import KOrganizationPrincipal, KTask, KTaskOwner
from ...schemas.task_owner import TaskOwnerCreate, TaskOwnerUpdate


async def add_task_owner(
    task_id: UUID,
    owner_data: TaskOwnerCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskOwner:
    """Add a new owner to a task.

    Args:
        task_id: ID of the task
        owner_data: Task owner creation data
        user_id: ID of the user adding the owner
        db: Database session

    Returns:
        The created task owner model

    Raises:
        TaskNotFoundException: If the task is not found
        PrincipalNotFoundException: If the principal is not found
        TaskOwnerAlreadyExistsException: If the owner already exists for the task
    """
    # Verify task exists and get its org_id
    stmt = select(KTask).where(KTask.id == task_id)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = task.org_id

    # Verify principal exists and belongs to the same org
    principal_stmt = select(KOrganizationPrincipal).where(
        KOrganizationPrincipal.principal_id == owner_data.principal_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.org_id == org_id,  # type: ignore[arg-type]
    )
    result = await db.execute(principal_stmt)
    org_principal = result.scalar_one_or_none()

    if not org_principal:
        raise PrincipalNotFoundException(
            principal_id=owner_data.principal_id, scope=str(org_id)
        )

    # Create new task owner with audit fields
    new_task_owner = KTaskOwner(
        task_id=task_id,
        principal_id=owner_data.principal_id,
        org_id=org_id,
        role=owner_data.role,
        meta=owner_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_task_owner)

    try:
        await db.commit()
        await db.refresh(new_task_owner)
    except IntegrityError as e:
        await db.rollback()
        raise TaskOwnerAlreadyExistsException(
            task_id=task_id,
            principal_id=owner_data.principal_id,
            scope=str(org_id),
        ) from e

    return new_task_owner


async def list_task_owners(task_id: UUID, db: AsyncSession) -> list[KTaskOwner]:
    """List all owners for a task.

    Args:
        task_id: ID of the task
        db: Database session

    Returns:
        List of task owner models

    Raises:
        TaskNotFoundException: If the task is not found
    """
    # Verify task exists
    stmt = select(KTask).where(KTask.id == task_id)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Get all owners for this task
    stmt = select(KTaskOwner).where(  # type: ignore[assignment]
        KTaskOwner.task_id == task_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    owners = result.scalars().all()
    return list(owners)  # type: ignore[arg-type]


async def get_task_owner(
    task_id: UUID, principal_id: UUID, db: AsyncSession
) -> KTaskOwner:
    """Get a single task owner relationship.

    Args:
        task_id: ID of the task
        principal_id: ID of the principal
        db: Database session

    Returns:
        The task owner model

    Raises:
        TaskOwnerNotFoundException: If the task owner relationship is not found
    """
    stmt = select(KTaskOwner).where(
        KTaskOwner.task_id == task_id,  # type: ignore[arg-type]
        KTaskOwner.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_owner = result.scalar_one_or_none()

    if not task_owner:
        raise TaskOwnerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope=None
        )

    return task_owner


async def update_task_owner(
    task_id: UUID,
    principal_id: UUID,
    owner_data: TaskOwnerUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskOwner:
    """Update a task owner relationship.

    Args:
        task_id: ID of the task
        principal_id: ID of the principal
        owner_data: Task owner update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated task owner model

    Raises:
        TaskOwnerNotFoundException: If the task owner relationship is not found
    """
    stmt = select(KTaskOwner).where(
        KTaskOwner.task_id == task_id,  # type: ignore[arg-type]
        KTaskOwner.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_owner = result.scalar_one_or_none()

    if not task_owner:
        raise TaskOwnerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope=None
        )

    # Update only provided fields
    if owner_data.role is not None:
        task_owner.role = owner_data.role
    if owner_data.meta is not None:
        task_owner.meta = owner_data.meta

    # Update audit fields
    task_owner.last_modified = datetime.now()
    task_owner.last_modified_by = user_id

    await db.commit()
    await db.refresh(task_owner)

    return task_owner


async def remove_task_owner(
    task_id: UUID, principal_id: UUID, db: AsyncSession
) -> None:
    """Remove an owner from a task.

    Args:
        task_id: ID of the task
        principal_id: ID of the principal
        db: Database session

    Raises:
        TaskOwnerNotFoundException: If the task owner relationship is not found
    """
    stmt = select(KTaskOwner).where(
        KTaskOwner.task_id == task_id,  # type: ignore[arg-type]
        KTaskOwner.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_owner = result.scalar_one_or_none()

    if not task_owner:
        raise TaskOwnerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope=None
        )

    await db.delete(task_owner)
    await db.commit()
