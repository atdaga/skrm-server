"""Business logic for organization management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    OrganizationAlreadyExistsException,
    OrganizationCreationFailedException,
    OrganizationNotFoundException,
    OrganizationUpdateConflictException,
)
from ...core.org_id import extract_org_prefix, generate_org_id
from ...models import KOrganization
from ...models.k_principal import SystemRole
from ...schemas.organization import OrganizationCreate, OrganizationUpdate
from ..deps import verify_organization_membership

MAX_RETRIES = 10


async def get_existing_org_prefixes(db: AsyncSession) -> set[str]:
    """Get all existing organization ID prefixes.

    Args:
        db: Database session

    Returns:
        Set of org ID prefixes (first 4 sections of each org's UUID)
    """
    stmt = select(KOrganization.id)  # type: ignore[call-overload]
    result = await db.execute(stmt)
    org_ids = result.scalars().all()

    return {extract_org_prefix(org_id) for org_id in org_ids}


async def create_organization(
    org_data: OrganizationCreate,
    user_id: UUID,
    scope: str,
    system_role: SystemRole,
    db: AsyncSession,
) -> KOrganization:
    """Create a new organization.

    Args:
        org_data: Organization creation data
        user_id: ID of the user creating the organization
        scope: Scope for multi-tenancy (currently unused for organizations)
        system_role: System role of the user
        db: Database session

    Returns:
        The created organization model

    Raises:
        InsufficientPrivilegesException: If user does not have SYSTEM or SYSTEM_ROOT role
        OrganizationAlreadyExistsException: If an organization with the same name or alias already exists
        OrganizationCreationFailedException: If organization creation fails after retries
    """
    # Check authorization: only SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN can create organizations
    if system_role not in (
        SystemRole.SYSTEM,
        SystemRole.SYSTEM_ROOT,
        SystemRole.SYSTEM_ADMIN,
    ):
        raise InsufficientPrivilegesException(
            required_privilege="SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN role",
            user_id=user_id,
        )

    # Get existing org prefixes to ensure uniqueness
    existing_prefixes = await get_existing_org_prefixes(db)

    for attempt in range(MAX_RETRIES):
        # Generate a new org ID with unique prefix
        org_id = generate_org_id()
        org_prefix = extract_org_prefix(org_id)

        # Check if prefix is unique (collision check before DB insert)
        if org_prefix in existing_prefixes:  # pragma: no cover
            continue  # Try again with a new ID

        # Create new organization with audit fields
        new_org = KOrganization(
            id=org_id,
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
            return new_org
        except IntegrityError as e:
            await db.rollback()
            # Determine which constraint failed based on error message
            error_msg = str(e.orig).lower()
            if "alias" in error_msg:
                raise OrganizationAlreadyExistsException(
                    identifier=org_data.alias, identifier_type="alias"
                ) from e
            elif "name" in error_msg:
                raise OrganizationAlreadyExistsException(
                    identifier=org_data.name, identifier_type="name"
                ) from e
            # ID collision - add prefix to set and retry
            existing_prefixes.add(org_prefix)  # pragma: no cover
            if attempt == MAX_RETRIES - 1:  # pragma: no cover
                raise OrganizationCreationFailedException(  # pragma: no cover
                    message=f"Failed to create organization after {MAX_RETRIES} retries due to ID prefix collisions"
                ) from None

    # This should never be reached, but type checker needs it
    raise OrganizationCreationFailedException(  # pragma: no cover
        message="Failed to create organization"
    )


async def list_organizations(scope: str, db: AsyncSession) -> list[KOrganization]:
    """List all organizations.

    Args:
        scope: Scope for multi-tenancy (currently unused for organizations)
        db: Database session

    Returns:
        List of organization models
    """
    stmt = select(KOrganization).where(KOrganization.deleted_at.is_(None))  # type: ignore[union-attr]
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

    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
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
    system_role: SystemRole,
    db: AsyncSession,
) -> KOrganization:
    """Update an organization.

    Args:
        org_id: ID of the organization to update
        org_data: Organization update data
        user_id: ID of the user performing the update
        scope: Scope for multi-tenancy (currently unused for organizations)
        system_role: System role of the user
        db: Database session

    Returns:
        The updated organization model

    Raises:
        InsufficientPrivilegesException: If user does not have SYSTEM or SYSTEM_ROOT role
        OrganizationNotFoundException: If the organization is not found
        OrganizationUpdateConflictException: If updating causes a name or alias conflict
    """
    # Check authorization: only SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN can update organizations
    if system_role not in (
        SystemRole.SYSTEM,
        SystemRole.SYSTEM_ROOT,
        SystemRole.SYSTEM_ADMIN,
    ):
        raise InsufficientPrivilegesException(
            required_privilege="SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN role",
            user_id=user_id,
        )

    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
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
    org_id: UUID,
    scope: str,
    user_id: UUID,
    system_role: SystemRole,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Delete an organization.

    Args:
        org_id: ID of the organization to delete
        scope: Scope for multi-tenancy (currently unused for organizations)
        user_id: ID of the user making the request
        system_role: System role of the user
        db: Database session
        hard_delete: If True, permanently delete the organization. If False, soft delete.

    Raises:
        InsufficientPrivilegesException: If user does not have SYSTEM or SYSTEM_ROOT role
        OrganizationNotFoundException: If the organization is not found
    """
    # Check authorization: only SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN can delete organizations
    if system_role not in (
        SystemRole.SYSTEM,
        SystemRole.SYSTEM_ROOT,
        SystemRole.SYSTEM_ADMIN,
    ):
        raise InsufficientPrivilegesException(
            required_privilege="SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN role",
            user_id=user_id,
        )

    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundException(org_id=org_id)

    if hard_delete:  # pragma: no cover
        await db.delete(org)  # pragma: no cover
    else:
        org.deleted_at = datetime.now()
        org.last_modified = datetime.now()
        org.last_modified_by = user_id
    await db.commit()
