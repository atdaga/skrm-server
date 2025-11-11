"""Organization principal management endpoints for adding, listing, updating, and removing organization principals."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    OrganizationNotFoundException,
    OrganizationPrincipalAlreadyExistsException,
    OrganizationPrincipalNotFoundException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import organization_principals as organization_principals_logic
from ...schemas.organization_principal import (
    OrganizationPrincipalCreate,
    OrganizationPrincipalDetail,
    OrganizationPrincipalList,
    OrganizationPrincipalUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(
    prefix="/organizations/{org_id}/principals", tags=["organization-principals"]
)


@router.post(
    "", response_model=OrganizationPrincipalDetail, status_code=status.HTTP_201_CREATED
)
async def add_organization_principal(
    org_id: UUID,
    principal_data: OrganizationPrincipalCreate,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPrincipalDetail:
    """Add a new principal to an organization.

    Requires system, systemRoot, or systemAdmin role.
    """
    user_id = current_user.id

    try:
        principal = await organization_principals_logic.add_organization_principal(
            org_id=org_id,
            principal_data=principal_data,
            user_id=user_id,
            system_role=current_user.system_role,
            db=db,
        )
        return OrganizationPrincipalDetail.model_validate(principal)
    except InsufficientPrivilegesException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
    except OrganizationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except OrganizationPrincipalAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=OrganizationPrincipalList)
async def list_organization_principals(
    org_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPrincipalList:
    """List all principals of an organization."""
    user_id = UUID(token_data.sub)

    try:
        principals = await organization_principals_logic.list_organization_principals(
            org_id=org_id, user_id=user_id, db=db
        )
        return OrganizationPrincipalList(
            principals=[
                OrganizationPrincipalDetail.model_validate(principal)
                for principal in principals
            ]
        )
    except OrganizationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{principal_id}", response_model=OrganizationPrincipalDetail)
async def get_organization_principal(
    org_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPrincipalDetail:
    """Get a single organization principal."""
    user_id = UUID(token_data.sub)

    try:
        principal = await organization_principals_logic.get_organization_principal(
            org_id=org_id,
            principal_id=principal_id,
            user_id=user_id,
            db=db,
        )
        return OrganizationPrincipalDetail.model_validate(principal)
    except OrganizationPrincipalNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{principal_id}", response_model=OrganizationPrincipalDetail)
async def update_organization_principal(
    org_id: UUID,
    principal_id: UUID,
    principal_data: OrganizationPrincipalUpdate,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPrincipalDetail:
    """Update an organization principal.

    Requires system, systemRoot, or systemAdmin role.
    """
    user_id = current_user.id

    try:
        principal = await organization_principals_logic.update_organization_principal(
            org_id=org_id,
            principal_id=principal_id,
            principal_data=principal_data,
            user_id=user_id,
            system_role=current_user.system_role,
            db=db,
        )
        return OrganizationPrincipalDetail.model_validate(principal)
    except InsufficientPrivilegesException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
    except OrganizationPrincipalNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{principal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_principal(
    org_id: UUID,
    principal_id: UUID,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the relationship")
    ] = False,
) -> None:
    """Remove a principal from an organization.

    Requires system, systemRoot, or systemAdmin role.
    For hard delete, requires system or systemRoot role.
    """
    user_id = current_user.id

    # Check authorization for hard delete
    if hard_delete:
        from ...logic import deps as deps_logic

        try:
            deps_logic.check_hard_delete_privileges(current_user)
        except InsufficientPrivilegesException as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await organization_principals_logic.remove_organization_principal(
            org_id=org_id,
            principal_id=principal_id,
            user_id=user_id,
            system_role=current_user.system_role,
            db=db,
            hard_delete=hard_delete,
        )
    except InsufficientPrivilegesException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
    except OrganizationPrincipalNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
