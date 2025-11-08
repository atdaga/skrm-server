"""Business logic for organization principal management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    OrganizationNotFoundException,
    OrganizationPrincipalAlreadyExistsException,
    OrganizationPrincipalNotFoundException,
)
from ...models import KOrganization, KOrganizationPrincipal
from ...schemas.organization_principal import (
    OrganizationPrincipalCreate,
    OrganizationPrincipalUpdate,
)
from ..deps import verify_organization_membership


async def add_organization_principal(
    org_id: UUID,
    principal_data: OrganizationPrincipalCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KOrganizationPrincipal:
    """Add a new principal to an organization.

    Args:
        org_id: ID of the organization
        principal_data: Organization principal creation data
        user_id: ID of the user adding the principal
        db: Database session

    Returns:
        The created organization principal model

    Raises:
        OrganizationNotFoundException: If the organization is not found
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        OrganizationPrincipalAlreadyExistsException: If the principal already exists in the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Verify organization exists
    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted == False)  # type: ignore[arg-type]  # noqa: E712
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
    stmt = select(KOrganization).where(KOrganization.id == org_id, KOrganization.deleted == False)  # type: ignore[arg-type]  # noqa: E712
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
    db: AsyncSession,
) -> KOrganizationPrincipal:
    """Update an organization principal.

    Args:
        org_id: ID of the organization
        principal_id: ID of the principal
        principal_data: Organization principal update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated organization principal model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        OrganizationPrincipalNotFoundException: If the organization principal is not found
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

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
    org_id: UUID, principal_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    """Remove a principal from an organization.

    Args:
        org_id: ID of the organization
        principal_id: ID of the principal
        user_id: ID of the user making the request
        db: Database session

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        OrganizationPrincipalNotFoundException: If the organization principal is not found
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

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

    await db.delete(principal)
    await db.commit()
