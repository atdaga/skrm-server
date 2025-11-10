"""Task reviewer management endpoints for adding, listing, updating, and removing task reviewers."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    PrincipalNotFoundException,
    TaskNotFoundException,
    TaskReviewerAlreadyExistsException,
    TaskReviewerNotFoundException,
)
from ...logic.v1 import task_reviewers as task_reviewers_logic
from ...schemas.task_reviewer import (
    TaskReviewerCreate,
    TaskReviewerDetail,
    TaskReviewerList,
    TaskReviewerUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/tasks/{task_id}/reviewers", tags=["task-reviewers"])


@router.post("", response_model=TaskReviewerDetail, status_code=status.HTTP_201_CREATED)
async def add_task_reviewer(
    task_id: UUID,
    reviewer_data: TaskReviewerCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskReviewerDetail:
    """Add a new reviewer to a task."""
    user_id = UUID(token_data.sub)

    try:
        task_reviewer = await task_reviewers_logic.add_task_reviewer(
            task_id=task_id,
            reviewer_data=reviewer_data,
            user_id=user_id,
            db=db,
        )
        return TaskReviewerDetail.model_validate(task_reviewer)
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
    except TaskReviewerAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=TaskReviewerList)
async def list_task_reviewers(
    task_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskReviewerList:
    """List all reviewers for a task."""
    try:
        reviewers = await task_reviewers_logic.list_task_reviewers(
            task_id=task_id, db=db
        )
        return TaskReviewerList(
            reviewers=[
                TaskReviewerDetail.model_validate(reviewer) for reviewer in reviewers
            ]
        )
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{principal_id}", response_model=TaskReviewerDetail)
async def get_task_reviewer(
    task_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskReviewerDetail:
    """Get a single task reviewer relationship."""
    try:
        task_reviewer = await task_reviewers_logic.get_task_reviewer(
            task_id=task_id,
            principal_id=principal_id,
            db=db,
        )
        return TaskReviewerDetail.model_validate(task_reviewer)
    except TaskReviewerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{principal_id}", response_model=TaskReviewerDetail)
async def update_task_reviewer(
    task_id: UUID,
    principal_id: UUID,
    reviewer_data: TaskReviewerUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskReviewerDetail:
    """Update a task reviewer relationship."""
    user_id = UUID(token_data.sub)

    try:
        task_reviewer = await task_reviewers_logic.update_task_reviewer(
            task_id=task_id,
            principal_id=principal_id,
            reviewer_data=reviewer_data,
            user_id=user_id,
            db=db,
        )
        return TaskReviewerDetail.model_validate(task_reviewer)
    except TaskReviewerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{principal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_reviewer(
    task_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the relationship")
    ] = False,
) -> None:
    """Remove a reviewer from a task."""
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
        await task_reviewers_logic.remove_task_reviewer(
            task_id=task_id,
            principal_id=principal_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except TaskReviewerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
