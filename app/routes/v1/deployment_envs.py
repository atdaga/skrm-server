"""Deployment environment management endpoints for creating, listing, updating, and deleting deployment environments."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    DeploymentEnvAlreadyExistsException,
    DeploymentEnvNotFoundException,
    DeploymentEnvUpdateConflictException,
    InsufficientPrivilegesException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import deployment_envs as deployment_envs_logic
from ...schemas.deployment_env import (
    DeploymentEnvCreate,
    DeploymentEnvDetail,
    DeploymentEnvList,
    DeploymentEnvUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/deployment-envs", tags=["deployment-envs"])


@router.post(
    "", response_model=DeploymentEnvDetail, status_code=status.HTTP_201_CREATED
)
async def create_deployment_env(
    deployment_env_data: DeploymentEnvCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentEnvDetail:
    """Create a new deployment environment."""
    user_id = UUID(token_data.sub)

    try:
        deployment_env = await deployment_envs_logic.create_deployment_env(
            deployment_env_data=deployment_env_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return DeploymentEnvDetail.model_validate(deployment_env)
    except DeploymentEnvAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=DeploymentEnvList)
async def list_deployment_envs(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentEnvList:
    """List all deployment environments in the given organization."""
    user_id = UUID(token_data.sub)

    try:
        deployment_envs = await deployment_envs_logic.list_deployment_envs(
            org_id=org_id, user_id=user_id, db=db
        )
        return DeploymentEnvList(
            deployment_envs=[
                DeploymentEnvDetail.model_validate(deployment_env)
                for deployment_env in deployment_envs
            ]
        )
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{deployment_env_id}", response_model=DeploymentEnvDetail)
async def get_deployment_env(
    deployment_env_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentEnvDetail:
    """Get a single deployment environment by ID."""
    user_id = UUID(token_data.sub)

    try:
        deployment_env = await deployment_envs_logic.get_deployment_env(
            deployment_env_id=deployment_env_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return DeploymentEnvDetail.model_validate(deployment_env)
    except DeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{deployment_env_id}", response_model=DeploymentEnvDetail)
async def update_deployment_env(
    deployment_env_id: UUID,
    deployment_env_data: DeploymentEnvUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentEnvDetail:
    """Update a deployment environment."""
    user_id = UUID(token_data.sub)

    try:
        deployment_env = await deployment_envs_logic.update_deployment_env(
            deployment_env_id=deployment_env_id,
            deployment_env_data=deployment_env_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return DeploymentEnvDetail.model_validate(deployment_env)
    except DeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except DeploymentEnvUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{deployment_env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment_env(
    deployment_env_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the deployment environment")
    ] = False,
) -> None:
    """Delete a deployment environment."""
    user_id = UUID(token_data.sub)

    # Check authorization for hard delete
    if hard_delete:
        from ...logic import deps as deps_logic

        try:
            deps_logic.check_hard_delete_privileges(current_user)
        except InsufficientPrivilegesException as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await deployment_envs_logic.delete_deployment_env(
            deployment_env_id=deployment_env_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except DeploymentEnvNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
