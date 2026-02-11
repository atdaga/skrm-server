"""Business logic for feature management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    FeatureAlreadyExistsException,
    FeatureCreationFailedException,
    FeatureNotFoundException,
    FeatureUpdateConflictException,
)
from ...core.feature_id import extract_feature_number, generate_feature_id
from ...models import KFeature
from ...schemas.feature import FeatureCreate, FeatureUpdate
from ..deps import verify_organization_membership

MAX_RETRIES = 10


async def get_next_feature_number(org_id: UUID, db: AsyncSession) -> int:
    """Get next feature number by finding max existing number + 1.

    Args:
        org_id: Organization ID to find features for
        db: Database session

    Returns:
        The next available feature number (1 if no features exist)
    """
    stmt = select(KFeature.id).where(  # type: ignore[call-overload]
        KFeature.org_id == org_id,
        KFeature.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    feature_ids = result.scalars().all()

    if not feature_ids:
        return 1

    max_number = max(extract_feature_number(fid) for fid in feature_ids)
    return max_number + 1


async def create_feature(
    feature_data: FeatureCreate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KFeature:
    """Create a new feature.

    Args:
        feature_data: Feature creation data
        user_id: ID of the user creating the feature
        org_id: Organization ID for the feature
        db: Database session

    Returns:
        The created feature model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        FeatureAlreadyExistsException: If a feature with the same name already exists in the organization
        FeatureCreationFailedException: If feature creation fails after retries
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    for attempt in range(MAX_RETRIES):
        try:
            next_number = await get_next_feature_number(org_id, db) + attempt
            feature_id = generate_feature_id(org_id, next_number)

            # Create new feature with audit fields
            new_feature = KFeature(
                id=feature_id,
                name=feature_data.name,
                org_id=org_id,
                parent=feature_data.parent,
                parent_path=feature_data.parent_path,
                feature_type=feature_data.feature_type,
                summary=feature_data.summary,
                details=feature_data.details,
                guestimate=feature_data.guestimate,
                derived_guestimate=feature_data.derived_guestimate,
                review_result=feature_data.review_result,
                meta=feature_data.meta,
                created_by=user_id,
                last_modified_by=user_id,
            )

            db.add(new_feature)

            if in_transaction:  # pragma: no cover - tested via txs integration
                # Already in a transaction (managed by txs), just flush
                await db.flush()  # pragma: no cover
            else:
                # No active transaction, commit our changes
                await db.commit()
            await db.refresh(new_feature)

            return new_feature
        except IntegrityError as e:
            if not in_transaction:  # pragma: no cover
                await db.rollback()  # pragma: no cover
            # Check if it's a name uniqueness violation vs ID collision
            error_str = str(e).lower()
            if "name" in error_str or "unique" in error_str:
                raise FeatureAlreadyExistsException(
                    name=feature_data.name, scope=str(org_id)
                ) from e
            # ID collision - retry with next number
            if attempt == MAX_RETRIES - 1:  # pragma: no cover
                raise FeatureCreationFailedException(  # pragma: no cover
                    message=f"Failed to create feature after {MAX_RETRIES} retries due to ID collisions",
                    org_id=org_id,
                ) from None
            continue  # pragma: no cover

    # This should never be reached, but type checker needs it
    raise FeatureCreationFailedException(  # pragma: no cover
        message="Failed to create feature", org_id=org_id
    )


async def list_features(
    org_id: UUID, user_id: UUID, db: AsyncSession
) -> list[KFeature]:
    """List all features in the given organization.

    Args:
        org_id: Organization ID to filter features by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of feature models

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KFeature).where(KFeature.org_id == org_id, KFeature.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    features = result.scalars().all()
    return list(features)


async def get_feature(
    feature_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> KFeature:
    """Get a single feature by ID.

    Args:
        feature_id: ID of the feature to retrieve
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The feature model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        FeatureNotFoundException: If the feature is not found in the given organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.org_id == org_id, KFeature.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=str(org_id))

    return feature


async def update_feature(
    feature_id: UUID,
    feature_data: FeatureUpdate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KFeature:
    """Update a feature.

    Args:
        feature_id: ID of the feature to update
        feature_data: Feature update data
        user_id: ID of the user performing the update
        org_id: Organization ID to filter by
        db: Database session

    Returns:
        The updated feature model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        FeatureNotFoundException: If the feature is not found
        FeatureUpdateConflictException: If updating causes a name conflict
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.org_id == org_id, KFeature.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=str(org_id))

    # Update only provided fields
    if feature_data.name is not None:
        feature.name = feature_data.name
    if feature_data.parent is not None:
        feature.parent = feature_data.parent
    if feature_data.parent_path is not None:
        feature.parent_path = feature_data.parent_path
    if feature_data.feature_type is not None:
        feature.feature_type = feature_data.feature_type
    if feature_data.summary is not None:
        feature.summary = feature_data.summary
    if feature_data.details is not None:
        feature.details = feature_data.details
    if feature_data.guestimate is not None:
        feature.guestimate = feature_data.guestimate
    if feature_data.derived_guestimate is not None:
        feature.derived_guestimate = feature_data.derived_guestimate
    if feature_data.review_result is not None:
        feature.review_result = feature_data.review_result
    if feature_data.meta is not None:
        feature.meta = feature_data.meta

    # Update audit fields
    feature.last_modified = datetime.now()
    feature.last_modified_by = user_id

    try:
        if in_transaction:  # pragma: no cover - tested via txs integration
            # Already in a transaction (managed by txs), just flush
            await db.flush()  # pragma: no cover
        else:  # pragma: no cover - hard to test due to autobegin
            # No active transaction, commit our changes
            await db.commit()  # pragma: no cover
        await db.refresh(feature)
    except IntegrityError as e:  # pragma: no cover
        if not in_transaction:  # pragma: no cover
            await db.rollback()  # pragma: no cover
        raise FeatureUpdateConflictException(  # pragma: no cover
            feature_id=feature_id,
            name=feature_data.name or feature.name,
            scope=str(org_id),
        ) from e

    return feature


async def delete_feature(
    feature_id: UUID,
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Delete a feature.

    Args:
        feature_id: ID of the feature to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the feature. If False, soft delete.

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        FeatureNotFoundException: If the feature is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.org_id == org_id, KFeature.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=str(org_id))

    if hard_delete:  # pragma: no cover
        await db.delete(feature)  # pragma: no cover
    else:
        feature.deleted_at = datetime.now()
        feature.last_modified = datetime.now()
        feature.last_modified_by = user_id
    if not in_transaction:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
