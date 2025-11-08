"""Task management endpoints for creating, listing, updating, and deleting tasks."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    TaskAlreadyExistsException,
    TaskNotFoundException,
    TaskUpdateConflictException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import tasks as tasks_logic
from ...schemas.task import TaskCreate, TaskDetail, TaskList, TaskUpdate
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDetail:
    """Create a new task."""
    user_id = UUID(token_data.sub)

    try:
        task = await tasks_logic.create_task(
            task_data=task_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return TaskDetail.model_validate(task)
    except TaskAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=TaskList)
async def list_tasks(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskList:
    """List all tasks in the given organization."""
    user_id = UUID(token_data.sub)

    try:
        tasks = await tasks_logic.list_tasks(org_id=org_id, user_id=user_id, db=db)
        return TaskList(tasks=[TaskDetail.model_validate(task) for task in tasks])
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDetail:
    """Get a single task by ID."""
    user_id = UUID(token_data.sub)

    try:
        task = await tasks_logic.get_task(
            task_id=task_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return TaskDetail.model_validate(task)
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{task_id}", response_model=TaskDetail)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDetail:
    """Update a task."""
    user_id = UUID(token_data.sub)

    try:
        task = await tasks_logic.update_task(
            task_id=task_id,
            task_data=task_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return TaskDetail.model_validate(task)
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TaskUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a task."""
    user_id = UUID(token_data.sub)

    try:
        await tasks_logic.delete_task(
            task_id=task_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
