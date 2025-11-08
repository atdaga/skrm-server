"""Business logic for feature management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    FeatureAlreadyExistsException,
    FeatureNotFoundException,
    FeatureUpdateConflictException,
)
from ...models import KFeature
from ...schemas.feature import FeatureCreate, FeatureUpdate
from ..deps import verify_organization_membership


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
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Create new feature with audit fields
    new_feature = KFeature(
        name=feature_data.name,
        org_id=org_id,
        parent=feature_data.parent,
        parent_path=feature_data.parent_path,
        feature_type=feature_data.feature_type,
        summary=feature_data.summary,
        notes=feature_data.notes,
        guestimate=feature_data.guestimate,
        derived_guestimate=feature_data.derived_guestimate,
        review_result=feature_data.review_result,
        meta=feature_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_feature)

    try:
        await db.commit()
        await db.refresh(new_feature)
    except IntegrityError as e:
        await db.rollback()
        raise FeatureAlreadyExistsException(
            name=feature_data.name, scope=str(org_id)
        ) from e

    return new_feature


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

    stmt = select(KFeature).where(KFeature.org_id == org_id, KFeature.deleted == False)  # type: ignore[arg-type]  # noqa: E712
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

    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.org_id == org_id, KFeature.deleted == False)  # type: ignore[arg-type]  # noqa: E712
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
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.org_id == org_id, KFeature.deleted == False)  # type: ignore[arg-type]  # noqa: E712
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
    if feature_data.notes is not None:
        feature.notes = feature_data.notes
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
        await db.commit()
        await db.refresh(feature)
    except IntegrityError as e:
        await db.rollback()
        raise FeatureUpdateConflictException(
            feature_id=feature_id,
            name=feature_data.name or feature.name,
            scope=str(org_id),
        ) from e

    return feature


async def delete_feature(
    feature_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    """Delete a feature.

    Args:
        feature_id: ID of the feature to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        FeatureNotFoundException: If the feature is not found
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.org_id == org_id, KFeature.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=str(org_id))

    await db.delete(feature)
    await db.commit()
