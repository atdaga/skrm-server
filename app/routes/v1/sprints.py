"""Sprint management endpoints for creating, listing, updating, and deleting sprints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    SprintNotFoundException,
    SprintUpdateConflictException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import sprints as sprints_logic
from ...schemas.sprint import SprintCreate, SprintDetail, SprintList, SprintUpdate
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/sprints", tags=["sprints"])


@router.post("", response_model=SprintDetail, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    sprint_data: SprintCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintDetail:
    """Create a new sprint."""
    user_id = UUID(token_data.sub)

    try:
        sprint = await sprints_logic.create_sprint(
            sprint_data=sprint_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return SprintDetail.model_validate(sprint)
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=SprintList)
async def list_sprints(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintList:
    """List all sprints in the given organization."""
    user_id = UUID(token_data.sub)

    try:
        sprints = await sprints_logic.list_sprints(
            org_id=org_id, user_id=user_id, db=db
        )
        return SprintList(
            sprints=[SprintDetail.model_validate(sprint) for sprint in sprints]
        )
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{sprint_id}", response_model=SprintDetail)
async def get_sprint(
    sprint_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintDetail:
    """Get a single sprint by ID."""
    user_id = UUID(token_data.sub)

    try:
        sprint = await sprints_logic.get_sprint(
            sprint_id=sprint_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return SprintDetail.model_validate(sprint)
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{sprint_id}", response_model=SprintDetail)
async def update_sprint(
    sprint_id: UUID,
    sprint_data: SprintUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintDetail:
    """Update a sprint."""
    user_id = UUID(token_data.sub)

    try:
        sprint = await sprints_logic.update_sprint(
            sprint_id=sprint_id,
            sprint_data=sprint_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return SprintDetail.model_validate(sprint)
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except SprintUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint(
    sprint_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[bool, Query(description="Hard delete the sprint")] = False,
) -> None:
    """Delete a sprint (cascades to sprint tasks and teams)."""
    user_id = UUID(token_data.sub)

    # Check authorization for hard delete
    if hard_delete:  # pragma: no cover
        from ...logic import deps as deps_logic  # pragma: no cover

        try:  # pragma: no cover
            deps_logic.check_hard_delete_privileges(current_user)  # pragma: no cover
        except InsufficientPrivilegesException as e:  # pragma: no cover
            raise HTTPException(  # pragma: no cover
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await sprints_logic.delete_sprint(
            sprint_id=sprint_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
