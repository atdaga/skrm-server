"""Task owner management endpoints for adding, listing, updating, and removing task owners."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    PrincipalNotFoundException,
    TaskNotFoundException,
    TaskOwnerAlreadyExistsException,
    TaskOwnerNotFoundException,
)
from ...logic.v1 import task_owners as task_owners_logic
from ...schemas.task_owner import (
    TaskOwnerCreate,
    TaskOwnerDetail,
    TaskOwnerList,
    TaskOwnerUpdate,
)
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/tasks/{task_id}/owners", tags=["task-owners"])


@router.post("", response_model=TaskOwnerDetail, status_code=status.HTTP_201_CREATED)
async def add_task_owner(
    task_id: UUID,
    owner_data: TaskOwnerCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOwnerDetail:
    """Add a new owner to a task."""
    user_id = UUID(token_data.sub)

    try:
        task_owner = await task_owners_logic.add_task_owner(
            task_id=task_id,
            owner_data=owner_data,
            user_id=user_id,
            db=db,
        )
        return TaskOwnerDetail.model_validate(task_owner)
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except PrincipalNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TaskOwnerAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=TaskOwnerList)
async def list_task_owners(
    task_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOwnerList:
    """List all owners for a task."""
    try:
        owners = await task_owners_logic.list_task_owners(task_id=task_id, db=db)
        return TaskOwnerList(
            owners=[TaskOwnerDetail.model_validate(owner) for owner in owners]
        )
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{principal_id}", response_model=TaskOwnerDetail)
async def get_task_owner(
    task_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOwnerDetail:
    """Get a single task owner relationship."""
    try:
        task_owner = await task_owners_logic.get_task_owner(
            task_id=task_id,
            principal_id=principal_id,
            db=db,
        )
        return TaskOwnerDetail.model_validate(task_owner)
    except TaskOwnerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{principal_id}", response_model=TaskOwnerDetail)
async def update_task_owner(
    task_id: UUID,
    principal_id: UUID,
    owner_data: TaskOwnerUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskOwnerDetail:
    """Update a task owner relationship."""
    user_id = UUID(token_data.sub)

    try:
        task_owner = await task_owners_logic.update_task_owner(
            task_id=task_id,
            principal_id=principal_id,
            owner_data=owner_data,
            user_id=user_id,
            db=db,
        )
        return TaskOwnerDetail.model_validate(task_owner)
    except TaskOwnerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{principal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_owner(
    task_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove an owner from a task."""
    try:
        await task_owners_logic.remove_task_owner(
            task_id=task_id,
            principal_id=principal_id,
            db=db,
        )
    except TaskOwnerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
