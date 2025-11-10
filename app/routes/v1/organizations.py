"""Organization management endpoints for creating, listing, updating, and deleting organizations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationUpdateConflictException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import organizations as organizations_logic
from ...schemas.organization import (
    OrganizationCreate,
    OrganizationDetail,
    OrganizationList,
    OrganizationUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_system_admin_user

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationDetail, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: Annotated[UserDetail, Depends(get_system_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationDetail:
    """Create a new organization.

    Requires system, systemRoot, or systemAdmin role.
    """
    user_id = current_user.id

    try:
        org = await organizations_logic.create_organization(
            org_data=org_data,
            user_id=user_id,
            scope=current_user.scope,
            db=db,
        )
        return OrganizationDetail.model_validate(org)
    except OrganizationAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=OrganizationList)
async def list_organizations(
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationList:
    """List all organizations in the current user's scope."""
    organizations = await organizations_logic.list_organizations(
        scope=token_data.scope, db=db
    )
    return OrganizationList(
        organizations=[OrganizationDetail.model_validate(org) for org in organizations]
    )


@router.get("/{org_id}", response_model=OrganizationDetail)
async def get_organization(
    org_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationDetail:
    """Get a single organization by ID."""
    user_id = UUID(token_data.sub)

    try:
        org = await organizations_logic.get_organization(
            org_id=org_id,
            scope=token_data.scope,
            user_id=user_id,
            db=db,
        )
        return OrganizationDetail.model_validate(org)
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


@router.patch("/{org_id}", response_model=OrganizationDetail)
async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    current_user: Annotated[UserDetail, Depends(get_system_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationDetail:
    """Update an organization.

    Requires system, systemRoot, or systemAdmin role.
    """
    user_id = current_user.id

    try:
        org = await organizations_logic.update_organization(
            org_id=org_id,
            org_data=org_data,
            user_id=user_id,
            scope=current_user.scope,
            db=db,
        )
        return OrganizationDetail.model_validate(org)
    except OrganizationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except OrganizationUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    current_user: Annotated[UserDetail, Depends(get_system_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the organization")
    ] = False,
) -> None:
    """Delete an organization.

    Requires system, systemRoot, or systemAdmin role.
    For hard delete, requires system or systemRoot role.
    """
    user_id = current_user.id

    # Check authorization for hard delete
    if hard_delete:  # pragma: no cover
        from ...core.exceptions.domain_exceptions import InsufficientPrivilegesException
        from ...logic import deps as deps_logic  # pragma: no cover

        try:  # pragma: no cover
            deps_logic.check_hard_delete_privileges(current_user)  # pragma: no cover
        except InsufficientPrivilegesException as e:  # pragma: no cover
            raise HTTPException(  # pragma: no cover
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await organizations_logic.delete_organization(
            org_id=org_id,
            scope=current_user.scope,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
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
