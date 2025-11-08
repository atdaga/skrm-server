"""Business logic for organization management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationUpdateConflictException,
)
from ...models import KOrganization
from ...schemas.organization import OrganizationCreate, OrganizationUpdate
from ..deps import verify_organization_membership


async def create_organization(
    org_data: OrganizationCreate,
    user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KOrganization:
    """Create a new organization.

    Args:
        org_data: Organization creation data
        user_id: ID of the user creating the organization
        scope: Scope for multi-tenancy (currently unused for organizations)
        db: Database session

    Returns:
        The created organization model

    Raises:
        OrganizationAlreadyExistsException: If an organization with the same name or alias already exists
    """
    # Create new organization with audit fields
    new_org = KOrganization(
        name=org_data.name,
        alias=org_data.alias,
        meta=org_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_org)

    try:
        await db.commit()
        await db.refresh(new_org)
    except IntegrityError as e:
        await db.rollback()
        # Determine which constraint failed based on error message
        error_msg = str(e.orig).lower()
        if "alias" in error_msg:
            raise OrganizationAlreadyExistsException(
                identifier=org_data.alias, identifier_type="alias"
            ) from e
        else:
            # Default to name constraint
            raise OrganizationAlreadyExistsException(
                identifier=org_data.name, identifier_type="name"
            ) from e

    return new_org


async def list_organizations(scope: str, db: AsyncSession) -> list[KOrganization]:
    """List all organizations.

    Args:
        scope: Scope for multi-tenancy (currently unused for organizations)
        db: Database session

    Returns:
        List of organization models
    """
    stmt = select(KOrganization).where(KOrganization.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    organizations = result.scalars().all()
    return list(organizations)


async def get_organization(
    org_id: UUID, scope: str, user_id: UUID, db: AsyncSession
) -> KOrganization:
    """Get a single organization by ID.

    Args:
        org_id: ID of the organization to retrieve
        scope: Scope for multi-tenancy (currently unused for organizations)
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The organization model

    Raises:
        OrganizationNotFoundException: If the organization is not found
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(org_id=org_id)

    return org


async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KOrganization:
    """Update an organization.

    Args:
        org_id: ID of the organization to update
        org_data: Organization update data
        user_id: ID of the user performing the update
        scope: Scope for multi-tenancy (currently unused for organizations)
        db: Database session

    Returns:
        The updated organization model

    Raises:
        OrganizationNotFoundException: If the organization is not found
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        OrganizationUpdateConflictException: If updating causes a name or alias conflict
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(org_id=org_id)

    # Update only provided fields
    if org_data.name is not None:
        org.name = org_data.name
    if org_data.alias is not None:
        org.alias = org_data.alias
    if org_data.meta is not None:
        org.meta = org_data.meta

    # Update audit fields
    org.last_modified = datetime.now()
    org.last_modified_by = user_id

    try:
        await db.commit()
        await db.refresh(org)
    except IntegrityError as e:
        await db.rollback()
        # Determine which constraint failed based on error message
        error_msg = str(e.orig).lower()
        if "alias" in error_msg:
            raise OrganizationUpdateConflictException(
                org_id=org_id,
                identifier=org_data.alias or org.alias,
                identifier_type="alias",
            ) from e
        else:
            # Default to name constraint
            raise OrganizationUpdateConflictException(
                org_id=org_id,
                identifier=org_data.name or org.name,
                identifier_type="name",
            ) from e

    return org


async def delete_organization(
    org_id: UUID, scope: str, user_id: UUID, db: AsyncSession
) -> None:
    """Delete an organization.

    Args:
        org_id: ID of the organization to delete
        scope: Scope for multi-tenancy (currently unused for organizations)
        user_id: ID of the user making the request
        db: Database session

    Raises:
        OrganizationNotFoundException: If the organization is not found
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(org_id=org_id)

    await db.delete(org)
    await db.commit()
