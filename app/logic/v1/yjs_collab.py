"""Business logic for Y.js document collaboration.

This module provides functions for managing Y.js document collaboration,
including document access, update management, and compaction operations.
"""

import time
from uuid import UUID

from pycrdt import merge_updates
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.logic.deps import verify_organization_membership
from app.models import KDoc, KDocYupdate

logger = get_logger(__name__)


async def get_doc_by_id(doc_id: UUID, db: AsyncSession) -> KDoc | None:
    """Get a document by ID.

    Args:
        doc_id: The document ID
        db: Database session

    Returns:
        The document if found, None otherwise
    """
    stmt = select(KDoc).where(KDoc.id == doc_id, KDoc.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_doc_for_collab(
    doc_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> KDoc | None:
    """Get document and verify user has access for collaboration.

    This function retrieves a document by ID and verifies that the user
    is a member of the organization that owns the document.

    Args:
        doc_id: The document ID
        user_id: The user ID to verify access for
        db: Database session

    Returns:
        The document if found and user is authorized, None if not found.

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member
            of the organization that owns the document.
    """
    doc = await get_doc_by_id(doc_id, db)
    if doc is None:
        return None

    await verify_organization_membership(doc.org_id, user_id, db)
    return doc


async def read_yupdates(
    doc_id: UUID,
    db: AsyncSession,
) -> list[tuple[bytes, bytes | None, float]]:
    """Read all Y.js updates for a document, ordered by timestamp.

    Args:
        doc_id: The document ID
        db: Database session

    Returns:
        List of tuples (yupdate, yupdate_meta, timestamp) ordered by timestamp
    """
    stmt = (
        select(KDocYupdate)
        .where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
        .order_by(KDocYupdate.timestamp)  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    return [(row.yupdate, row.yupdate_meta, row.timestamp) for row in result.scalars()]


async def write_yupdate(
    doc_id: UUID,
    org_id: UUID,
    user_id: UUID,
    yupdate: bytes,
    yupdate_meta: bytes | None,
    db: AsyncSession,
) -> None:
    """Write a Y.js update to the database.

    Args:
        doc_id: The document ID
        org_id: The organization ID (for audit trail)
        user_id: The user ID (for audit trail)
        yupdate: The Y.js update bytes
        yupdate_meta: Optional metadata bytes
        db: Database session
    """
    update = KDocYupdate(
        doc_id=doc_id,
        org_id=org_id,
        yupdate=yupdate,
        yupdate_meta=yupdate_meta,
        timestamp=time.time(),
        created_by=user_id,
        last_modified_by=user_id,
    )
    db.add(update)
    await db.commit()


async def get_doc_update_count(doc_id: UUID, db: AsyncSession) -> int:
    """Get the count of Y.js updates for a document.

    Args:
        doc_id: The document ID
        db: Database session

    Returns:
        Number of Y.js updates stored for the document
    """
    stmt = select(func.count()).where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_document_state(doc_id: UUID, db: AsyncSession) -> bytes | None:
    """Get the current document state as a merged Y.js update.

    This function reads all updates for a document and merges them into
    a single update that represents the current document state.

    Args:
        doc_id: The document ID
        db: Database session

    Returns:
        The merged document state as bytes, or None if no updates exist
    """
    stmt = (
        select(KDocYupdate.yupdate)  # type: ignore[call-overload]
        .where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[union-attr]
        .order_by(KDocYupdate.timestamp)
    )
    result = await db.execute(stmt)
    updates: list[bytes] = [row[0] for row in result.all()]

    if not updates:
        return None

    # If only one update, return it directly
    if len(updates) == 1:
        return updates[0]

    return merge_updates(updates)  # type: ignore[arg-type]  # pragma: no cover


async def compact_doc_updates(  # pragma: no cover
    doc_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> int:
    """Compact all Y.js updates for a document into a single snapshot.

    This function merges all updates into a single update and replaces
    all existing updates with the compacted version. This reduces storage
    and improves initial document load time.

    Args:
        doc_id: The document ID
        user_id: The user performing the compaction (for audit trail)
        db: Database session

    Returns:
        Number of updates that were compacted (0 if nothing to compact)
    """
    # Get the document to get org_id
    doc = await get_doc_by_id(doc_id, db)
    if doc is None:
        logger.warning("Cannot compact updates: document not found", doc_id=str(doc_id))
        return 0

    # Read all updates
    stmt = (
        select(KDocYupdate)
        .where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
        .order_by(KDocYupdate.timestamp)  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    updates_records = list(result.scalars())

    if len(updates_records) <= 1:
        return 0  # Nothing to compact

    # Merge all updates
    updates = [record.yupdate for record in updates_records]
    merged_update = merge_updates(updates)  # type: ignore[arg-type]

    original_count = len(updates)
    original_size = sum(len(u) for u in updates)

    # Delete old updates
    delete_stmt = delete(KDocYupdate).where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    await db.execute(delete_stmt)

    # Write compacted update
    current_time = time.time()
    compacted = KDocYupdate(
        doc_id=doc_id,
        org_id=doc.org_id,
        yupdate=merged_update,
        yupdate_meta=None,
        timestamp=current_time,
        created_by=user_id,
        last_modified_by=user_id,
    )
    db.add(compacted)
    await db.commit()

    logger.info(
        "Compacted Y.js updates",
        doc_id=str(doc_id),
        original_count=original_count,
        original_size=original_size,
        compacted_size=len(merged_update),
    )

    return original_count


async def delete_doc_updates(doc_id: UUID, db: AsyncSession) -> int:  # pragma: no cover
    """Delete all Y.js updates for a document.

    This is typically called when a document is deleted to clean up
    the associated Y.js updates.

    Args:
        doc_id: The document ID
        db: Database session

    Returns:
        Number of updates deleted
    """
    # Count updates first
    count_stmt = select(func.count()).where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    count_result = await db.execute(count_stmt)
    count = count_result.scalar_one()

    if count == 0:
        return 0

    # Delete updates
    delete_stmt = delete(KDocYupdate).where(KDocYupdate.doc_id == doc_id, KDocYupdate.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    await db.execute(delete_stmt)
    await db.commit()

    logger.info(
        "Deleted Y.js updates",
        doc_id=str(doc_id),
        count=count,
    )

    return count


__all__ = [
    "compact_doc_updates",
    "delete_doc_updates",
    "get_doc_by_id",
    "get_doc_for_collab",
    "get_doc_update_count",
    "get_document_state",
    "read_yupdates",
    "write_yupdate",
]
