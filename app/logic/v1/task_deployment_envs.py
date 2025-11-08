"""Business logic for task deployment environment management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    DeploymentEnvNotFoundException,
    TaskDeploymentEnvAlreadyExistsException,
    TaskDeploymentEnvNotFoundException,
    TaskNotFoundException,
)
from ...models import KDeploymentEnv, KTask, KTaskDeploymentEnv
from ...schemas.task_deployment_env import (
    TaskDeploymentEnvCreate,
    TaskDeploymentEnvUpdate,
)


async def add_task_deployment_env(
    task_id: UUID,
    deployment_env_data: TaskDeploymentEnvCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskDeploymentEnv:
    """Add a new deployment environment to a task.

    Args:
        task_id: ID of the task
        deployment_env_data: Task deployment environment creation data
        user_id: ID of the user adding the deployment environment
        db: Database session

    Returns:
        The created task deployment environment model

    Raises:
        TaskNotFoundException: If the task is not found
        DeploymentEnvNotFoundException: If the deployment environment is not found
        TaskDeploymentEnvAlreadyExistsException: If the deployment environment already exists for the task
    """
    # Verify task exists and get its org_id
    stmt = select(KTask).where(KTask.id == task_id)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = task.org_id

    # Verify deployment environment exists and belongs to the same org
    deployment_env_stmt = select(KDeploymentEnv).where(
        KDeploymentEnv.id == deployment_env_data.deployment_env_id,  # type: ignore[arg-type]
        KDeploymentEnv.org_id == org_id,  # type: ignore[arg-type]
    )
    result = await db.execute(deployment_env_stmt)
    deployment_env = result.scalar_one_or_none()

    if not deployment_env:
        raise DeploymentEnvNotFoundException(
            deployment_env_id=deployment_env_data.deployment_env_id, scope=str(org_id)
        )

    # Create new task deployment environment with audit fields
    new_task_deployment_env = KTaskDeploymentEnv(
        task_id=task_id,
        deployment_env_id=deployment_env_data.deployment_env_id,
        org_id=org_id,
        role=deployment_env_data.role,
        meta=deployment_env_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_task_deployment_env)

    try:
        await db.commit()
        await db.refresh(new_task_deployment_env)
    except IntegrityError as e:
        await db.rollback()
        raise TaskDeploymentEnvAlreadyExistsException(
            task_id=task_id,
            deployment_env_id=deployment_env_data.deployment_env_id,
            scope=str(org_id),
        ) from e

    return new_task_deployment_env


async def list_task_deployment_envs(
    task_id: UUID, db: AsyncSession
) -> list[KTaskDeploymentEnv]:
    """List all deployment environments for a task.

    Args:
        task_id: ID of the task
        db: Database session

    Returns:
        List of task deployment environment models

    Raises:
        TaskNotFoundException: If the task is not found
    """
    # Verify task exists
    stmt = select(KTask).where(KTask.id == task_id)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Get all deployment environments for this task
    stmt = select(KTaskDeploymentEnv).where(  # type: ignore[assignment]
        KTaskDeploymentEnv.task_id == task_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    deployment_envs = result.scalars().all()
    return list(deployment_envs)  # type: ignore[arg-type]


async def get_task_deployment_env(
    task_id: UUID, deployment_env_id: UUID, db: AsyncSession
) -> KTaskDeploymentEnv:
    """Get a single task deployment environment relationship.

    Args:
        task_id: ID of the task
        deployment_env_id: ID of the deployment environment
        db: Database session

    Returns:
        The task deployment environment model

    Raises:
        TaskDeploymentEnvNotFoundException: If the task deployment environment relationship is not found
    """
    stmt = select(KTaskDeploymentEnv).where(
        KTaskDeploymentEnv.task_id == task_id,  # type: ignore[arg-type]
        KTaskDeploymentEnv.deployment_env_id == deployment_env_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_deployment_env = result.scalar_one_or_none()

    if not task_deployment_env:
        raise TaskDeploymentEnvNotFoundException(
            task_id=task_id, deployment_env_id=deployment_env_id, scope=None
        )

    return task_deployment_env


async def update_task_deployment_env(
    task_id: UUID,
    deployment_env_id: UUID,
    deployment_env_data: TaskDeploymentEnvUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskDeploymentEnv:
    """Update a task deployment environment relationship.

    Args:
        task_id: ID of the task
        deployment_env_id: ID of the deployment environment
        deployment_env_data: Task deployment environment update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated task deployment environment model

    Raises:
        TaskDeploymentEnvNotFoundException: If the task deployment environment relationship is not found
    """
    stmt = select(KTaskDeploymentEnv).where(
        KTaskDeploymentEnv.task_id == task_id,  # type: ignore[arg-type]
        KTaskDeploymentEnv.deployment_env_id == deployment_env_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_deployment_env = result.scalar_one_or_none()

    if not task_deployment_env:
        raise TaskDeploymentEnvNotFoundException(
            task_id=task_id, deployment_env_id=deployment_env_id, scope=None
        )

    # Update only provided fields
    if deployment_env_data.role is not None:
        task_deployment_env.role = deployment_env_data.role
    if deployment_env_data.meta is not None:
        task_deployment_env.meta = deployment_env_data.meta

    # Update audit fields
    task_deployment_env.last_modified = datetime.now()
    task_deployment_env.last_modified_by = user_id

    await db.commit()
    await db.refresh(task_deployment_env)

    return task_deployment_env


async def remove_task_deployment_env(
    task_id: UUID, deployment_env_id: UUID, db: AsyncSession
) -> None:
    """Remove a deployment environment from a task.

    Args:
        task_id: ID of the task
        deployment_env_id: ID of the deployment environment
        db: Database session

    Raises:
        TaskDeploymentEnvNotFoundException: If the task deployment environment relationship is not found
    """
    stmt = select(KTaskDeploymentEnv).where(
        KTaskDeploymentEnv.task_id == task_id,  # type: ignore[arg-type]
        KTaskDeploymentEnv.deployment_env_id == deployment_env_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_deployment_env = result.scalar_one_or_none()

    if not task_deployment_env:
        raise TaskDeploymentEnvNotFoundException(
            task_id=task_id, deployment_env_id=deployment_env_id, scope=None
        )

    await db.delete(task_deployment_env)
    await db.commit()
