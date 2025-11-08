"""Task deployment environment management endpoints for adding, listing, updating, and removing task deployment environments."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    DeploymentEnvNotFoundException,
    TaskDeploymentEnvAlreadyExistsException,
    TaskDeploymentEnvNotFoundException,
    TaskNotFoundException,
)
from ...logic.v1 import task_deployment_envs as task_deployment_envs_logic
from ...schemas.task_deployment_env import (
    TaskDeploymentEnvCreate,
    TaskDeploymentEnvDetail,
    TaskDeploymentEnvList,
    TaskDeploymentEnvUpdate,
)
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(
    prefix="/tasks/{task_id}/deployment_envs", tags=["task-deployment-envs"]
)


@router.post(
    "", response_model=TaskDeploymentEnvDetail, status_code=status.HTTP_201_CREATED
)
async def add_task_deployment_env(
    task_id: UUID,
    deployment_env_data: TaskDeploymentEnvCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDeploymentEnvDetail:
    """Add a new deployment environment to a task."""
    user_id = UUID(token_data.sub)

    try:
        task_deployment_env = await task_deployment_envs_logic.add_task_deployment_env(
            task_id=task_id,
            deployment_env_data=deployment_env_data,
            user_id=user_id,
            db=db,
        )
        return TaskDeploymentEnvDetail.model_validate(task_deployment_env)
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except DeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TaskDeploymentEnvAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=TaskDeploymentEnvList)
async def list_task_deployment_envs(
    task_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDeploymentEnvList:
    """List all deployment environments for a task."""
    try:
        deployment_envs = await task_deployment_envs_logic.list_task_deployment_envs(
            task_id=task_id, db=db
        )
        return TaskDeploymentEnvList(
            deployment_envs=[
                TaskDeploymentEnvDetail.model_validate(env) for env in deployment_envs
            ]
        )
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{deployment_env_id}", response_model=TaskDeploymentEnvDetail)
async def get_task_deployment_env(
    task_id: UUID,
    deployment_env_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDeploymentEnvDetail:
    """Get a single task deployment environment relationship."""
    try:
        task_deployment_env = await task_deployment_envs_logic.get_task_deployment_env(
            task_id=task_id,
            deployment_env_id=deployment_env_id,
            db=db,
        )
        return TaskDeploymentEnvDetail.model_validate(task_deployment_env)
    except TaskDeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{deployment_env_id}", response_model=TaskDeploymentEnvDetail)
async def update_task_deployment_env(
    task_id: UUID,
    deployment_env_id: UUID,
    deployment_env_data: TaskDeploymentEnvUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskDeploymentEnvDetail:
    """Update a task deployment environment relationship."""
    user_id = UUID(token_data.sub)

    try:
        task_deployment_env = (
            await task_deployment_envs_logic.update_task_deployment_env(
                task_id=task_id,
                deployment_env_id=deployment_env_id,
                deployment_env_data=deployment_env_data,
                user_id=user_id,
                db=db,
            )
        )
        return TaskDeploymentEnvDetail.model_validate(task_deployment_env)
    except TaskDeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{deployment_env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_deployment_env(
    task_id: UUID,
    deployment_env_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a deployment environment from a task."""
    try:
        await task_deployment_envs_logic.remove_task_deployment_env(
            task_id=task_id,
            deployment_env_id=deployment_env_id,
            db=db,
        )
    except TaskDeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
