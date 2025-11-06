"""Project management endpoints for creating, listing, updating, and deleting projects."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    ProjectAlreadyExistsException,
    ProjectNotFoundException,
    ProjectUpdateConflictException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import projects as projects_logic
from ...schemas.project import ProjectCreate, ProjectDetail, ProjectList, ProjectUpdate
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetail:
    """Create a new project."""
    user_id = UUID(token_data.sub)

    try:
        project = await projects_logic.create_project(
            project_data=project_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return ProjectDetail.model_validate(project)
    except ProjectAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=ProjectList)
async def list_projects(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectList:
    """List all projects in the given organization."""
    user_id = UUID(token_data.sub)

    try:
        projects = await projects_logic.list_projects(
            org_id=org_id, user_id=user_id, db=db
        )
        return ProjectList(
            projects=[ProjectDetail.model_validate(project) for project in projects]
        )
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetail:
    """Get a single project by ID."""
    user_id = UUID(token_data.sub)

    try:
        project = await projects_logic.get_project(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return ProjectDetail.model_validate(project)
    except ProjectNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetail:
    """Update a project."""
    user_id = UUID(token_data.sub)

    try:
        project = await projects_logic.update_project(
            project_id=project_id,
            project_data=project_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return ProjectDetail.model_validate(project)
    except ProjectNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except ProjectUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a project (cascades to project teams)."""
    user_id = UUID(token_data.sub)

    try:
        await projects_logic.delete_project(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
    except ProjectNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
