"""Organization principal management endpoints for adding, listing, updating, and removing organization principals."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
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
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(
    prefix="/organizations/{org_id}/principals", tags=["organization-principals"]
)


@router.post(
    "", response_model=OrganizationPrincipalDetail, status_code=status.HTTP_201_CREATED
)
async def add_organization_principal(
    org_id: UUID,
    principal_data: OrganizationPrincipalCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPrincipalDetail:
    """Add a new principal to an organization."""
    user_id = UUID(token_data.sub)

    try:
        principal = await organization_principals_logic.add_organization_principal(
            org_id=org_id,
            principal_data=principal_data,
            user_id=user_id,
            db=db,
        )
        return OrganizationPrincipalDetail.model_validate(principal)
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
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPrincipalDetail:
    """Update an organization principal."""
    user_id = UUID(token_data.sub)

    try:
        principal = await organization_principals_logic.update_organization_principal(
            org_id=org_id,
            principal_id=principal_id,
            principal_data=principal_data,
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


@router.delete("/{principal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_principal(
    org_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a principal from an organization."""
    user_id = UUID(token_data.sub)

    try:
        await organization_principals_logic.remove_organization_principal(
            org_id=org_id,
            principal_id=principal_id,
            user_id=user_id,
            db=db,
        )
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
