"""Business logic for feature doc relationship management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    DocNotFoundException,
    FeatureDocAlreadyExistsException,
    FeatureDocNotFoundException,
    FeatureNotFoundException,
)
from ...models import KDoc, KFeature, KFeatureDoc
from ...schemas.feature_doc import FeatureDocCreate, FeatureDocUpdate


async def add_feature_doc(
    feature_id: UUID,
    doc_data: FeatureDocCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KFeatureDoc:
    """Add a new doc to a feature.

    Args:
        feature_id: ID of the feature
        doc_data: Feature doc creation data
        user_id: ID of the user adding the doc
        db: Database session

    Returns:
        The created feature doc model

    Raises:
        FeatureNotFoundException: If the feature is not found
        DocNotFoundException: If the doc is not found
        FeatureDocAlreadyExistsException: If the doc already exists for the feature
    """
    # Verify feature exists and get its org_id
    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = feature.org_id

    # Verify doc exists and belongs to the same org
    doc_stmt = select(KDoc).where(
        KDoc.id == doc_data.doc_id,  # type: ignore[arg-type]
        KDoc.org_id == org_id,  # type: ignore[arg-type]
        KDoc.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(doc_stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise DocNotFoundException(doc_id=doc_data.doc_id, scope=str(org_id))

    # Create new feature doc with audit fields
    new_feature_doc = KFeatureDoc(
        feature_id=feature_id,
        doc_id=doc_data.doc_id,
        org_id=org_id,
        role=doc_data.role,
        meta=doc_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_feature_doc)

    try:
        await db.commit()
        await db.refresh(new_feature_doc)
    except IntegrityError as e:
        await db.rollback()
        raise FeatureDocAlreadyExistsException(
            feature_id=feature_id, doc_id=doc_data.doc_id, scope=str(org_id)
        ) from e

    return new_feature_doc


async def list_feature_docs(feature_id: UUID, db: AsyncSession) -> list[KFeatureDoc]:
    """List all docs for a feature.

    Args:
        feature_id: ID of the feature
        db: Database session

    Returns:
        List of feature doc models

    Raises:
        FeatureNotFoundException: If the feature is not found
    """
    # Verify feature exists
    stmt = select(KFeature).where(KFeature.id == feature_id, KFeature.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    feature = result.scalar_one_or_none()

    if not feature:
        raise FeatureNotFoundException(feature_id=feature_id, scope=None)

    # Get all docs for this feature
    stmt = select(KFeatureDoc).where(  # type: ignore[assignment]
        KFeatureDoc.feature_id == feature_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return list(docs)  # type: ignore[arg-type]


async def get_feature_doc(
    feature_id: UUID, doc_id: UUID, db: AsyncSession
) -> KFeatureDoc:
    """Get a single feature doc relationship.

    Args:
        feature_id: ID of the feature
        doc_id: ID of the doc
        db: Database session

    Returns:
        The feature doc model

    Raises:
        FeatureDocNotFoundException: If the feature doc relationship is not found
    """
    stmt = select(KFeatureDoc).where(
        KFeatureDoc.feature_id == feature_id,  # type: ignore[arg-type]
        KFeatureDoc.doc_id == doc_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    feature_doc = result.scalar_one_or_none()

    if not feature_doc:
        raise FeatureDocNotFoundException(
            feature_id=feature_id, doc_id=doc_id, scope=None
        )

    return feature_doc


async def update_feature_doc(
    feature_id: UUID,
    doc_id: UUID,
    doc_data: FeatureDocUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KFeatureDoc:
    """Update a feature doc relationship.

    Args:
        feature_id: ID of the feature
        doc_id: ID of the doc
        doc_data: Feature doc update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated feature doc model

    Raises:
        FeatureDocNotFoundException: If the feature doc relationship is not found
    """
    stmt = select(KFeatureDoc).where(
        KFeatureDoc.feature_id == feature_id,  # type: ignore[arg-type]
        KFeatureDoc.doc_id == doc_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    feature_doc = result.scalar_one_or_none()

    if not feature_doc:
        raise FeatureDocNotFoundException(
            feature_id=feature_id, doc_id=doc_id, scope=None
        )

    # Update only provided fields
    if doc_data.role is not None:
        feature_doc.role = doc_data.role
    if doc_data.meta is not None:
        feature_doc.meta = doc_data.meta

    # Update audit fields
    feature_doc.last_modified = datetime.now()
    feature_doc.last_modified_by = user_id

    await db.commit()
    await db.refresh(feature_doc)

    return feature_doc


async def remove_feature_doc(feature_id: UUID, doc_id: UUID, db: AsyncSession) -> None:
    """Remove a doc from a feature.

    Args:
        feature_id: ID of the feature
        doc_id: ID of the doc
        db: Database session

    Raises:
        FeatureDocNotFoundException: If the feature doc relationship is not found
    """
    stmt = select(KFeatureDoc).where(
        KFeatureDoc.feature_id == feature_id,  # type: ignore[arg-type]
        KFeatureDoc.doc_id == doc_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    feature_doc = result.scalar_one_or_none()

    if not feature_doc:
        raise FeatureDocNotFoundException(
            feature_id=feature_id, doc_id=doc_id, scope=None
        )

    await db.delete(feature_doc)
    await db.commit()
