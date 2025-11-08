"""Task feature management endpoints for adding, listing, updating, and removing task features."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    FeatureNotFoundException,
    TaskFeatureAlreadyExistsException,
    TaskFeatureNotFoundException,
    TaskNotFoundException,
)
from ...logic.v1 import task_features as task_features_logic
from ...schemas.task_feature import (
    TaskFeatureCreate,
    TaskFeatureDetail,
    TaskFeatureList,
    TaskFeatureUpdate,
)
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/tasks/{task_id}/features", tags=["task-features"])


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a feature from a task."""
    try:
        await task_features_logic.remove_task_feature(
            task_id=task_id,
            feature_id=feature_id,
            db=db,
        )
    except TaskFeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
