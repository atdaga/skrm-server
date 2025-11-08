"""Sprint task management endpoints for adding, listing, updating, and removing tasks from sprints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    SprintNotFoundException,
    SprintTaskAlreadyExistsException,
    SprintTaskNotFoundException,
    TaskNotFoundException,
)
from ...logic.v1 import sprint_tasks as sprint_tasks_logic
from ...schemas.sprint_task import (
    SprintTaskCreate,
    SprintTaskDetail,
    SprintTaskList,
    SprintTaskUpdate,
)
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/sprints/{sprint_id}/tasks", tags=["sprint-tasks"])


@router.post("", response_model=SprintTaskDetail, status_code=status.HTTP_201_CREATED)
async def add_sprint_task(
    sprint_id: UUID,
    task_data: SprintTaskCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTaskDetail:
    """Add a task to a sprint."""
    user_id = UUID(token_data.sub)

    try:
        sprint_task = await sprint_tasks_logic.add_sprint_task(
            sprint_id=sprint_id,
            task_data=task_data,
            user_id=user_id,
            db=db,
        )
        return SprintTaskDetail.model_validate(sprint_task)
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except SprintTaskAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=SprintTaskList)
async def list_sprint_tasks(
    sprint_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTaskList:
    """List all tasks in a sprint."""
    try:
        tasks = await sprint_tasks_logic.list_sprint_tasks(sprint_id=sprint_id, db=db)
        return SprintTaskList(
            tasks=[SprintTaskDetail.model_validate(task) for task in tasks]
        )
    except SprintNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{task_id}", response_model=SprintTaskDetail)
async def get_sprint_task(
    sprint_id: UUID,
    task_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTaskDetail:
    """Get a single sprint task."""
    try:
        sprint_task = await sprint_tasks_logic.get_sprint_task(
            sprint_id=sprint_id,
            task_id=task_id,
            db=db,
        )
        return SprintTaskDetail.model_validate(sprint_task)
    except SprintTaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{task_id}", response_model=SprintTaskDetail)
async def update_sprint_task(
    sprint_id: UUID,
    task_id: UUID,
    task_data: SprintTaskUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SprintTaskDetail:
    """Update a sprint task."""
    user_id = UUID(token_data.sub)

    try:
        sprint_task = await sprint_tasks_logic.update_sprint_task(
            sprint_id=sprint_id,
            task_id=task_id,
            task_data=task_data,
            user_id=user_id,
            db=db,
        )
        return SprintTaskDetail.model_validate(sprint_task)
    except SprintTaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_sprint_task(
    sprint_id: UUID,
    task_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a task from a sprint."""
    try:
        await sprint_tasks_logic.remove_sprint_task(
            sprint_id=sprint_id,
            task_id=task_id,
            db=db,
        )
    except SprintTaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
