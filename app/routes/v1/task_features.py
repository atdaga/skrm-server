"""Task feature management endpoints for adding, listing, updating, and removing task features."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    FeatureNotFoundException,
    InsufficientPrivilegesException,
    TaskFeatureAlreadyExistsException,
    TaskFeatureNotFoundException,
    TaskNotFoundException,
)
from ...logic.v1 import task_features as task_features_logic
from ...schemas.task import TaskDetail, TaskList
from ...schemas.task_feature import (
    TaskFeatureCreate,
    TaskFeatureDetail,
    TaskFeatureList,
    TaskFeatureUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/tasks/{task_id}/features", tags=["task-features"])
feature_tasks_router = APIRouter(prefix="/tasks/feature", tags=["task-features"])


@router.post("", response_model=TaskFeatureDetail, status_code=status.HTTP_201_CREATED)
async def add_task_feature(
    task_id: UUID,
    feature_data: TaskFeatureCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskFeatureDetail:
    """Add a new feature to a task."""
    user_id = UUID(token_data.sub)

    try:
        task_feature = await task_features_logic.add_task_feature(
            task_id=task_id,
            feature_data=feature_data,
            user_id=user_id,
            db=db,
        )
        return TaskFeatureDetail.model_validate(task_feature)
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TaskFeatureAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=TaskFeatureList)
async def list_task_features(
    task_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskFeatureList:
    """List all features for a task."""
    try:
        features = await task_features_logic.list_task_features(task_id=task_id, db=db)
        return TaskFeatureList(
            features=[TaskFeatureDetail.model_validate(feature) for feature in features]
        )
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{feature_id}", response_model=TaskFeatureDetail)
async def get_task_feature(
    task_id: UUID,
    feature_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskFeatureDetail:
    """Get a single task feature relationship."""
    try:
        task_feature = await task_features_logic.get_task_feature(
            task_id=task_id,
            feature_id=feature_id,
            db=db,
        )
        return TaskFeatureDetail.model_validate(task_feature)
    except TaskFeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{feature_id}", response_model=TaskFeatureDetail)
async def update_task_feature(
    task_id: UUID,
    feature_id: UUID,
    feature_data: TaskFeatureUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskFeatureDetail:
    """Update a task feature relationship."""
    user_id = UUID(token_data.sub)

    try:
        task_feature = await task_features_logic.update_task_feature(
            task_id=task_id,
            feature_id=feature_id,
            feature_data=feature_data,
            user_id=user_id,
            db=db,
        )
        return TaskFeatureDetail.model_validate(task_feature)
    except TaskFeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_feature(
    task_id: UUID,
    feature_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the relationship")
    ] = False,
) -> None:
    """Remove a feature from a task."""
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
        await task_features_logic.remove_task_feature(
            task_id=task_id,
            feature_id=feature_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except TaskFeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@feature_tasks_router.get("/{feature_id}", response_model=TaskList | TaskFeatureList)
async def list_tasks_by_feature(
    feature_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    detail: Annotated[
        bool,
        Query(
            description="Return full task details (true) or junction records (false)"
        ),
    ] = True,
) -> TaskList | TaskFeatureList:
    """List all tasks associated with a feature."""
    try:
        if detail:
            tasks = await task_features_logic.list_tasks_by_feature_detailed(
                feature_id=feature_id, db=db
            )
            return TaskList(tasks=[TaskDetail.model_validate(t) for t in tasks])
        else:
            task_features = await task_features_logic.list_tasks_by_feature(
                feature_id=feature_id, db=db
            )
            return TaskFeatureList(
                features=[TaskFeatureDetail.model_validate(tf) for tf in task_features]
            )
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
