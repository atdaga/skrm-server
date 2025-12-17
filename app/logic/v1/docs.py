"""Business logic for doc management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    DocAlreadyExistsException,
    DocNotFoundException,
    DocUpdateConflictException,
)
from ...models import KDoc
from ...schemas.doc import DocCreate, DocUpdate
from ..deps import verify_organization_membership


async def create_doc(
    doc_data: DocCreate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KDoc:
    """Create a new doc.

    Args:
        doc_data: Doc creation data
        user_id: ID of the user creating the doc
        org_id: Organization ID for the doc
        db: Database session
    Returns:
        The created doc model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DocAlreadyExistsException: If a doc with the same name already exists in the organization
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Create new doc with audit fields
    new_doc = KDoc(
        name=doc_data.name,
        description=doc_data.description,
        content=doc_data.content,
        org_id=org_id,
        meta=doc_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_doc)

    try:
        if in_transaction:  # pragma: no cover - tested via txs integration
            # Already in a transaction (managed by txs), just flush
            await db.flush()  # pragma: no cover
        else:
            # No active transaction, commit our changes
            await db.commit()
        await db.refresh(new_doc)
    except IntegrityError as e:  # pragma: no cover
        if not in_transaction:  # pragma: no cover
            await db.rollback()  # pragma: no cover
        raise DocAlreadyExistsException(
            name=doc_data.name, scope=str(org_id)
        ) from e  # pragma: no cover

    return new_doc


async def list_docs(org_id: UUID, user_id: UUID, db: AsyncSession) -> list[KDoc]:
    """List all docs in the given organization.

    Args:
        org_id: Organization ID to filter docs by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of doc models

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDoc).where(KDoc.org_id == org_id, KDoc.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return list(docs)


async def get_doc(doc_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession) -> KDoc:
    """Get a single doc by ID.

    Args:
        doc_id: ID of the doc to retrieve
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The doc model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DocNotFoundException: If the doc is not found in the given organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDoc).where(KDoc.id == doc_id, KDoc.org_id == org_id, KDoc.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise DocNotFoundException(doc_id=doc_id, scope=str(org_id))

    return doc


async def update_doc(
    doc_id: UUID,
    doc_data: DocUpdate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KDoc:
    """Update a doc.

    Args:
        doc_id: ID of the doc to update
        doc_data: Doc update data
        user_id: ID of the user performing the update
        org_id: Organization ID to filter by
        db: Database session
    Returns:
        The updated doc model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DocNotFoundException: If the doc is not found
        DocUpdateConflictException: If updating causes a name conflict
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDoc).where(KDoc.id == doc_id, KDoc.org_id == org_id, KDoc.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise DocNotFoundException(doc_id=doc_id, scope=str(org_id))

    # Update only provided fields
    if doc_data.name is not None:
        doc.name = doc_data.name
    if doc_data.description is not None:
        doc.description = doc_data.description
    if doc_data.content is not None:
        doc.content = doc_data.content
    if doc_data.meta is not None:
        doc.meta = doc_data.meta

    # Update audit fields
    doc.last_modified = datetime.now()
    doc.last_modified_by = user_id

    try:
        if in_transaction:  # pragma: no cover - tested via txs integration
            # Already in a transaction (managed by txs), just flush
            await db.flush()  # pragma: no cover
        else:  # pragma: no cover - hard to test due to autobegin
            # No active transaction, commit our changes
            await db.commit()  # pragma: no cover
        await db.refresh(doc)
    except IntegrityError as e:  # pragma: no cover
        if not in_transaction:  # pragma: no cover
            await db.rollback()  # pragma: no cover
        raise DocUpdateConflictException(  # pragma: no cover
            doc_id=doc_id,
            name=doc_data.name or doc.name,
            scope=str(org_id),
        ) from e

    return doc


async def delete_doc(
    doc_id: UUID,
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Delete a doc.

    Args:
        doc_id: ID of the doc to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the doc. If False, soft delete.

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        DocNotFoundException: If the doc is not found
    """
    # Check if we're already in a transaction (e.g., from txs module)
    in_transaction = db.in_transaction()

    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KDoc).where(KDoc.id == doc_id, KDoc.org_id == org_id, KDoc.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise DocNotFoundException(doc_id=doc_id, scope=str(org_id))

    if hard_delete:  # pragma: no cover
        await db.delete(doc)  # pragma: no cover
    else:
        doc.deleted_at = datetime.now()
        doc.last_modified = datetime.now()
        doc.last_modified_by = user_id
    if not in_transaction:  # pragma: no cover - hard to test due to autobegin
        # No active transaction, commit our changes
        await db.commit()  # pragma: no cover
