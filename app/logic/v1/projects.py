"""Business logic for project management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    ProjectAlreadyExistsException,
    ProjectNotFoundException,
    ProjectUpdateConflictException,
)
from ...models import KProject
from ...schemas.project import ProjectCreate, ProjectUpdate
from ..deps import verify_organization_membership


async def create_project(
    project_data: ProjectCreate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KProject:
    """Create a new project.

    Args:
        project_data: Project creation data
        user_id: ID of the user creating the project
        org_id: Organization ID for the project
        db: Database session

    Returns:
        The created project model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        ProjectAlreadyExistsException: If a project with the same name already exists in the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    # Create new project with audit fields
    new_project = KProject(
        name=project_data.name,
        description=project_data.description,
        org_id=org_id,
        meta=project_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_project)

    try:
        await db.commit()
        await db.refresh(new_project)
    except IntegrityError as e:
        await db.rollback()
        raise ProjectAlreadyExistsException(
            name=project_data.name, scope=str(org_id)
        ) from e

    return new_project


async def list_projects(
    org_id: UUID, user_id: UUID, db: AsyncSession
) -> list[KProject]:
    """List all projects in the given organization.

    Args:
        org_id: Organization ID to filter projects by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        List of project models

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KProject).where(KProject.org_id == org_id, KProject.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    projects = result.scalars().all()
    return list(projects)


async def get_project(
    project_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> KProject:
    """Get a single project by ID.

    Args:
        project_id: ID of the project to retrieve
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Returns:
        The project model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        ProjectNotFoundException: If the project is not found in the given organization
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KProject).where(KProject.id == project_id, KProject.org_id == org_id, KProject.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id, scope=str(org_id))

    return project


async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    user_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> KProject:
    """Update a project.

    Args:
        project_id: ID of the project to update
        project_data: Project update data
        user_id: ID of the user performing the update
        org_id: Organization ID to filter by
        db: Database session

    Returns:
        The updated project model

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        ProjectNotFoundException: If the project is not found
        ProjectUpdateConflictException: If updating causes a name conflict
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KProject).where(KProject.id == project_id, KProject.org_id == org_id, KProject.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id, scope=str(org_id))

    # Update only provided fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.meta is not None:
        project.meta = project_data.meta

    # Update audit fields
    project.last_modified = datetime.now()
    project.last_modified_by = user_id

    try:
        await db.commit()
        await db.refresh(project)
    except IntegrityError as e:
        await db.rollback()
        raise ProjectUpdateConflictException(
            project_id=project_id,
            name=project_data.name or project.name,
            scope=str(org_id),
        ) from e

    return project


async def delete_project(
    project_id: UUID, org_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    """Delete a project.

    Args:
        project_id: ID of the project to delete
        org_id: Organization ID to filter by
        user_id: ID of the user making the request
        db: Database session

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
        ProjectNotFoundException: If the project is not found
    """
    # Verify user has access to this organization
    await verify_organization_membership(org_id=org_id, user_id=user_id, db=db)

    stmt = select(KProject).where(KProject.id == project_id, KProject.org_id == org_id, KProject.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id, scope=str(org_id))

    await db.delete(project)
    await db.commit()
