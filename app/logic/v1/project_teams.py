"""Business logic for project team management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    ProjectNotFoundException,
    ProjectTeamAlreadyExistsException,
    ProjectTeamNotFoundException,
)
from ...models import KProject, KProjectTeam
from ...schemas.project_team import ProjectTeamCreate, ProjectTeamUpdate


async def add_project_team(
    project_id: UUID,
    team_data: ProjectTeamCreate,
    user_id: UUID,
    db: AsyncSession,
) -> KProjectTeam:
    """Add a new team to a project.

    Args:
        project_id: ID of the project
        team_data: Project team creation data
        user_id: ID of the user adding the team
        db: Database session

    Returns:
        The created project team model

    Raises:
        ProjectNotFoundException: If the project is not found
        ProjectTeamAlreadyExistsException: If the team already exists in the project
    """
    # Verify project exists and get its org_id
    stmt = select(KProject).where(KProject.id == project_id, KProject.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id, scope=None)

    # Store org_id to avoid lazy loading issues
    org_id = project.org_id

    # Create new project team with audit fields
    new_team = KProjectTeam(
        project_id=project_id,
        team_id=team_data.team_id,
        org_id=org_id,
        role=team_data.role,
        meta=team_data.meta,
        created_by=user_id,
        last_modified_by=user_id,
    )

    db.add(new_team)

    try:
        await db.commit()
        await db.refresh(new_team)
    except IntegrityError as e:
        await db.rollback()
        raise ProjectTeamAlreadyExistsException(
            project_id=project_id, team_id=team_data.team_id, scope=str(org_id)
        ) from e

    return new_team


async def list_project_teams(project_id: UUID, db: AsyncSession) -> list[KProjectTeam]:
    """List all teams of a project.

    Args:
        project_id: ID of the project
        db: Database session

    Returns:
        List of project team models

    Raises:
        ProjectNotFoundException: If the project is not found
    """
    # Verify project exists and get its org_id
    stmt = select(KProject).where(KProject.id == project_id, KProject.deleted_at.is_(None))  # type: ignore[arg-type,union-attr]
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise ProjectNotFoundException(project_id=project_id, scope=None)

    # Get all teams for this project
    stmt = select(KProjectTeam).where(  # type: ignore[assignment]
        KProjectTeam.project_id == project_id  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    teams = result.scalars().all()
    return list(teams)  # type: ignore[arg-type]


async def get_project_team(
    project_id: UUID, team_id: UUID, db: AsyncSession
) -> KProjectTeam:
    """Get a single project team.

    Args:
        project_id: ID of the project
        team_id: ID of the team
        db: Database session

    Returns:
        The project team model

    Raises:
        ProjectTeamNotFoundException: If the project team is not found
    """
    stmt = select(KProjectTeam).where(
        KProjectTeam.project_id == project_id,  # type: ignore[arg-type]
        KProjectTeam.team_id == team_id,  # type: ignore[arg-type]
        KProjectTeam.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise ProjectTeamNotFoundException(
            project_id=project_id, team_id=team_id, scope=None
        )

    return team


async def update_project_team(
    project_id: UUID,
    team_id: UUID,
    team_data: ProjectTeamUpdate,
    user_id: UUID,
    db: AsyncSession,
) -> KProjectTeam:
    """Update a project team.

    Args:
        project_id: ID of the project
        team_id: ID of the team
        team_data: Project team update data
        user_id: ID of the user performing the update
        db: Database session

    Returns:
        The updated project team model

    Raises:
        ProjectTeamNotFoundException: If the project team is not found
    """
    stmt = select(KProjectTeam).where(
        KProjectTeam.project_id == project_id,  # type: ignore[arg-type]
        KProjectTeam.team_id == team_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise ProjectTeamNotFoundException(
            project_id=project_id, team_id=team_id, scope=None
        )

    # Update only provided fields
    if team_data.role is not None:
        team.role = team_data.role
    if team_data.meta is not None:
        team.meta = team_data.meta

    # Update audit fields
    team.last_modified = datetime.now()
    team.last_modified_by = user_id

    await db.commit()
    await db.refresh(team)

    return team


async def remove_project_team(
    project_id: UUID,
    team_id: UUID,
    user_id: UUID,
    db: AsyncSession,
    hard_delete: bool = False,
) -> None:
    """Remove a team from a project.

    Args:
        project_id: ID of the project
        team_id: ID of the team
        user_id: ID of the user making the request
        db: Database session
        hard_delete: If True, permanently delete the relationship. If False, soft delete.

    Raises:
        ProjectTeamNotFoundException: If the project team is not found
    """
    stmt = select(KProjectTeam).where(
        KProjectTeam.project_id == project_id,  # type: ignore[arg-type]
        KProjectTeam.team_id == team_id,  # type: ignore[arg-type]
        KProjectTeam.deleted_at.is_(None),  # type: ignore[union-attr]
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise ProjectTeamNotFoundException(
            project_id=project_id, team_id=team_id, scope=None
        )

    if hard_delete:  # pragma: no cover
        await db.delete(team)  # pragma: no cover
    else:
        team.deleted_at = datetime.now()
        team.last_modified = datetime.now()
        team.last_modified_by = user_id
    await db.commit()
