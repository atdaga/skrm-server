"""Business logic for task feature management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    FeatureNotFoundException,
    TaskFeatureAlreadyExistsException,
    TaskFeatureNotFoundException,
    TaskNotFoundException,
)
from ...models import KFeature, KTask, KTaskFeature
from ...schemas.task_feature import TaskFeatureCreate, TaskFeatureUpdate


async def add_task_feature(
    task_id: UUID,
    feature_data: TaskFeatureCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskFeature:
    """Add a new feature to a task.

    Args:
        task_id: ID of the task
        feature_data: Task feature creation data
        user_id: ID of the user adding the feature
        db: Database session
    Returns:
        The created task feature model

    Raises:
        TaskNotFoundException: If the task is not found
        FeatureNotFoundException: If the feature is not found
        TaskFeatureAlreadyExistsException: If the feature already exists for the task
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify task exists and get its org_id
    stmt = select(KTask).where(KTask.id == task_id, KTask.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = task.org_id

    # Verify feature exists and belongs to the same org
    feature_stmt = select(KFeature).where(
        KFeature.id == feature_data.feature_id,  # type: ignore[arg-type]
        KFeature.org_id == org_id,  # type: ignore[arg-type]
        KFeature.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(feature_stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(
            feature_id=feature_data.feature_id, scope=str(org_id)
        )

    # Create new task feature with audit fields
    new_task_feature = KTaskFeature(
        task_id=task_id,
        feature_id=feature_data.feature_id,
        org_id=org_id,
        role=feature_data.role,
        meta=feature_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_task_feature)

    try:
        if in_transaction:  # pragma: no cover - tested via txs integration
            # Already in a transaction (managed by txs), just flush
            await db.flush()  # pragma: no cover
        else:  # pragma: no cover - hard to test due to autobegin
            # No active transaction, commit our changes
            await db.commit()  # pragma: no cover
        await db.refresh(new_task_feature)
    except IntegrityError as e:
        if not in_transaction:  # pragma: no cover
            await db.rollback()  # pragma: no cover
        raise TaskFeatureAlreadyExistsException(
            task_id=task_id,
            feature_id=feature_data.feature_id,
            scope=str(org_id),
        ) from e

    return new_task_feature


async def list_task_features(task_id: UUID, db: AsyncSession) -> list[KTaskFeature]:
    """List all features for a task.

    Args:
        task_id: ID of the task
        db: Database session

    Returns:
        List of task feature models

    Raises:
        TaskNotFoundException: If the task is not found
    """
    # Verify task exists
    stmt = select(KTask).where(KTask.id == task_id, KTask.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundException(task_id=task_id, scope=None)

    # Get all features for this task
    stmt = select(KTaskFeature).where(  # type: ignore[assignment]
        KTaskFeature.task_id == task_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    features = result.scalars().all()
    return list(features)  # type: ignore[arg-type]


async def get_task_feature(
    task_id: UUID, feature_id: UUID, db: AsyncSession
) -> KTaskFeature:
    """Get a single task feature relationship.

    Args:
        task_id: ID of the task
        feature_id: ID of the feature
        db: Database session

    Returns:
        The task feature model

    Raises:
        TaskFeatureNotFoundException: If the task feature relationship is not found
    """
    stmt = select(KTaskFeature).where(
        KTaskFeature.task_id == task_id,  # type: ignore[arg-type]
        KTaskFeature.feature_id == feature_id,  # type: ignore[arg-type]
        KTaskFeature.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    task_feature = result.scalar_one_or_none()

    if not task_feature:
        raise TaskFeatureNotFoundException(
            task_id=task_id, feature_id=feature_id, scope=None
        )

    return task_feature


async def update_task_feature(
    task_id: UUID,
    feature_id: UUID,
    feature_data: TaskFeatureUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KTaskFeature:
    """Update a task feature relationship.

    Args:
        task_id: ID of the task
        feature_id: ID of the feature
        feature_data: Task feature update data
        user_id: ID of the user performing the update
        db: Database session
    Returns:
        The updated task feature model

    Raises:
        TaskFeatureNotFoundException: If the task feature relationship is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    stmt = select(KTaskFeature).where(
        KTaskFeature.task_id == task_id,  # type: ignore[arg-type]
        KTaskFeature.feature_id == feature_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_feature = result.scalar_one_or_none()

    if not task_feature:
        raise TaskFeatureNotFoundException(
            task_id=task_id, feature_id=feature_id, scope=None
        )

    # Update only provided fields
    if feature_data.role is not None:
        task_feature.role = feature_data.role
    if feature_data.meta is not None:
        task_feature.meta = feature_data.meta

    # Update audit fields
    task_feature.last_modified = datetime.now()
    task_feature.last_modified_by = user_id

    if in_transaction:  # pragma: no cover - tested via txs integration
        # Already in a transaction (managed by txs), just flush
        await db.flush()  # pragma: no cover
    else:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
    await db.refresh(task_feature)

    return task_feature


async def list_tasks_by_feature(
    feature_id: UUID, db: AsyncSession
) -> list[KTaskFeature]:
    """List all tasks associated with a feature.

    Args:
        feature_id: ID of the feature
        db: Database session

    Returns:
        List of task feature models

    Raises:
        FeatureNotFoundException: If the feature is not found
    """
    # Verify feature exists
    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=None)

    # Get all task-feature records for this feature
    stmt = select(KTaskFeature).where(  # type: ignore[assignment]
        KTaskFeature.feature_id == feature_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    task_features = result.scalars().all()
    return list(task_features)  # type: ignore[arg-type]


async def list_tasks_by_feature_detailed(
    feature_id: UUID, db: AsyncSession
) -> list[KTask]:
    """List all tasks associated with a feature, returning full task objects.

    Args:
        feature_id: ID of the feature
        db: Database session

    Returns:
        List of task models

    Raises:
        FeatureNotFoundException: If the feature is not found
    """
    # Verify feature exists
    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=None)

    # Join KTaskFeature → KTask to get full task objects
    task_stmt = (
        select(KTask)
        .join(KTaskFeature, KTaskFeature.task_id == KTask.id)  # type: ignore[arg-type]
        .where(
            KTaskFeature.feature_id == feature_id,  # type: ignore[arg-type]
            KTaskFeature.deleted_at.is_(None),  # type: ignore[union-attr]
            KTask.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    )
    result = await db.execute(task_stmt)
    tasks = result.scalars().all()
    return list(tasks)  # type: ignore[arg-type]


async def remove_task_feature(
    task_id: UUID,
    feature_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Remove a feature from a task.

    Args:
        task_id: ID of the task
        feature_id: ID of the feature
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the relationship. If False, soft delete.

    Raises:
        TaskFeatureNotFoundException: If the task feature relationship is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    stmt = select(KTaskFeature).where(
        KTaskFeature.task_id == task_id,  # type: ignore[arg-type]
        KTaskFeature.feature_id == feature_id,  # type: ignore[arg-type]
        KTaskFeature.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    task_feature = result.scalar_one_or_none()

    if not task_feature:
        raise TaskFeatureNotFoundException(
            task_id=task_id, feature_id=feature_id, scope=None
        )

    if hard_delete:  # pragma: no cover
        await db.delete(task_feature)  # pragma: no cover
    else:
        task_feature.deleted_at = datetime.now()
        task_feature.last_modified = datetime.now()
        task_feature.last_modified_by = user_id
    if not in_transaction:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
