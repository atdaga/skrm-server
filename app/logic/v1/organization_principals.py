"""Business logic for organization principal management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    OrganizationNotFoundException,
    OrganizationPrincipalAlreadyExistsException,
    OrganizationPrincipalNotFoundException,
)
from ...models import KOrganization, KOrganizationPrincipal
from ...models.k_principal import SystemRole
from ...schemas.organization_principal import (
    OrganizationPrincipalCreate,
    OrganizationPrincipalUpdate,
)
from ..deps import verify_organization_membership


async def add_organization_principal(
    org_id: UUID,
    principal_data: OrganizationPrincipalCreate,
    user_id: UUID,
    system_role: SystemRole,
    db: AsyncSession,
) -> KOrganizationPrincipal:
    """Add a new principal to an organization.

    Args:
        org_id: ID of the organization
        principal_data: Organization principal creation data
        user_id: ID of the user adding the principal
        system_role: System role of the user
        db: Database session

    Returns:
        The created organization principal model

    Raises:
        InsufficientPrivilegesException: If user does not have SYSTEM or SYSTEM_ROOT role
        OrganizationNotFoundException: If the organization is not found
        OrganizationPrincipalAlreadyExistsException: If the principal already exists in the organization
    """
    # Check authorization: only SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN can add organization principals
    if system_role not in (SystemRole.SYSTEM, SystemRole.SYSTEM_ROOT, SystemRole.SYSTEM_ADMIN):
        raise InsufficientPrivilegesException(
            required_privilege="SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN role",
            user_id=user_id,
        )

    # Verify organization exists
    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    organization = result.scalar_one_or_none()

    if not organization:
        raise OrganizationNotFoundException(org_id=org_id, scope=None)

    # Create new organization principal with audit fields
    new_principal = KOrganizationPrincipal(
        org_id=org_id,
        principal_id=principal_data.principal_id,
        role=principal_data.role,
        meta=principal_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_principal)

    try:
        await db.commit()
        await db.refresh(new_principal)
    except IntegrityError as e:
        await db.rollback()
        raise OrganizationPrincipalAlreadyExistsException(
            org_id=org_id, principal_id=principal_data.principal_id, scope=str(org_id)
        ) from e

    return new_principal


async def list_organization_principals(
    org_id: UUID, user_id: UUID, db: AsyncSession
) -> list[KOrganizationPrincipal]:
    """List all principals of an organization.

    Args:
        org_id: ID of the organization
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of organization principal models

    Raises:
        OrganizationNotFoundException: If the organization is not found
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Verify organization exists
    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    organization = result.scalar_one_or_none()

    if not organization:
        raise OrganizationNotFoundException(org_id=org_id, scope=None)

    # Get all principals for this organization
    stmt = select(KOrganizationPrincipal).where(  # type: ignore[assignment]
        KOrganizationPrincipal.org_id == org_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    principals = result.scalars().all()
    return list(principals)  # type: ignore[arg-type]


async def get_organization_principal(
    org_id: UUID, principal_id: UUID, user_id: UUID, db: AsyncSession
) -> KOrganizationPrincipal:
    """Get a single organization principal.

    Args:
        org_id: ID of the organization
        principal_id: ID of the principal
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The organization principal model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        OrganizationPrincipalNotFoundException: If the organization principal is not found
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KOrganizationPrincipal).where(
        KOrganizationPrincipal.org_id == org_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.principal_id == principal_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    principal = result.scalar_one_or_none()

    if not principal:
        raise OrganizationPrincipalNotFoundException(
            org_id=org_id, principal_id=principal_id, scope=None
        )

    return principal


async def update_organization_principal(
    org_id: UUID,
    principal_id: UUID,
    principal_data: OrganizationPrincipalUpdate,
    user_id: UUID,
    system_role: SystemRole,
    db: AsyncSession,
) -> KOrganizationPrincipal:
    """Update an organization principal.

    Args:
        org_id: ID of the organization
        principal_id: ID of the principal
        principal_data: Organization principal update data
        user_id: ID of the user performing the update
        system_role: System role of the user
        db: Database session

    Returns:
        The updated organization principal model

    Raises:
        InsufficientPrivilegesException: If user does not have SYSTEM or SYSTEM_ROOT role
        OrganizationPrincipalNotFoundException: If the organization principal is not found
    """
    # Check authorization: only SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN can update organization principals
    if system_role not in (SystemRole.SYSTEM, SystemRole.SYSTEM_ROOT, SystemRole.SYSTEM_ADMIN):
        raise InsufficientPrivilegesException(
            required_privilege="SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN role",
            user_id=user_id,
        )

    stmt = select(KOrganizationPrincipal).where(
        KOrganizationPrincipal.org_id == org_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.principal_id == principal_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    principal = result.scalar_one_or_none()

    if not principal:
        raise OrganizationPrincipalNotFoundException(
            org_id=org_id, principal_id=principal_id, scope=None
        )

    # Update only provided fields
    if principal_data.role is not None:
        principal.role = principal_data.role
    if principal_data.meta is not None:
        principal.meta = principal_data.meta

    # Update audit fields
    principal.last_modified = datetime.now()
    principal.last_modified_by = user_id

    await db.commit()
    await db.refresh(principal)

    return principal


async def remove_organization_principal(
    org_id: UUID,
    principal_id: UUID,
    user_id: UUID,
    system_role: SystemRole,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Remove a principal from an organization.

    Args:
        org_id: ID of the organization
        principal_id: ID of the principal
        user_id: ID of the user making the request
        system_role: System role of the user
        db: Database session
        hard_delete: If True, permanently delete the relationship. If False, soft delete.

    Raises:
        InsufficientPrivilegesException: If user does not have SYSTEM or SYSTEM_ROOT role
        OrganizationPrincipalNotFoundException: If the organization principal is not found
    """
    # Check authorization: only SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN can remove organization principals
    if system_role not in (SystemRole.SYSTEM, SystemRole.SYSTEM_ROOT, SystemRole.SYSTEM_ADMIN):
        raise InsufficientPrivilegesException(
            required_privilege="SYSTEM, SYSTEM_ROOT, or SYSTEM_ADMIN role",
            user_id=user_id,
        )

    stmt = select(KOrganizationPrincipal).where(
        KOrganizationPrincipal.org_id == org_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.principal_id == principal_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    principal = result.scalar_one_or_none()

    if not principal:
        raise OrganizationPrincipalNotFoundException(
            org_id=org_id, principal_id=principal_id, scope=None
        )

    if hard_delete:  # pragma: no cover
        await db.delete(principal)  # pragma: no cover
    else:
        principal.deleted_at = datetime.now()
        principal.last_modified = datetime.now()
        principal.last_modified_by = user_id
    await db.commit()
