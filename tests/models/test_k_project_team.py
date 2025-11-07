"""Unit tests for KProjectTeam model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KProject, KProjectTeam, KTeam


class TestKProjectTeamModel:
    """Test suite for KProjectTeam model."""

    @pytest.fixture
    async def project(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KProject:
        """Create a test project."""
        project = KProject(
            name="Test Project",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project

    @pytest.fixture
    async def team(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KTeam:
        """Create a test team."""
        team = KTeam(
            name="Test Team",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team)
        await session.commit()
        await session.refresh(team)
        return team

    @pytest.mark.asyncio
    async def test_create_project_team_with_required_fields(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a project team with only required fields."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()
        await session.refresh(project_team)

        assert project_team.project_id == project.id
        assert project_team.team_id == team.id
        assert project_team.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_project_team_default_values(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()
        await session.refresh(project_team)

        assert project_team.role is None
        assert project_team.meta == {}
        assert isinstance(project_team.created, datetime)
        assert isinstance(project_team.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_project_team_with_role(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a project team with a role."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="development",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()
        await session.refresh(project_team)

        assert project_team.role == "development"

    @pytest.mark.asyncio
    async def test_project_team_with_meta_data(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a project team with metadata."""
        meta_data = {
            "access_level": "full",
            "start_date": "2024-01-01",
            "responsibilities": ["backend", "testing"],
        }

        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="qa",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()
        await session.refresh(project_team)

        assert project_team.meta == meta_data

    @pytest.mark.asyncio
    async def test_project_team_composite_primary_key(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that project_id and team_id form a composite primary key."""
        project_team1 = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(project_team1)

        # Try to create another project_team with the same project_id and team_id
        project_team2 = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_project_team_audit_fields(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()
        await session.refresh(project_team)

        assert project_team.created_by == creator_id
        assert project_team.last_modified_by == creator_id

        # Update the project team
        project_team.role = "lead"
        project_team.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(project_team)

        assert project_team.created_by == creator_id  # Should not change
        assert project_team.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_project_team_cascade_delete_from_project(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a project cascades to project teams but not the team."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()

        # Delete the project
        await session.delete(project)
        await session.commit()

        # Verify project team is deleted
        result_exec = await session.execute(
            select(KProjectTeam).where(KProjectTeam.project_id == project.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify team still exists
        await session.refresh(team)
        assert team.id == team.id

    @pytest.mark.asyncio
    async def test_project_team_cascade_delete_from_team(
        self,
        session: AsyncSession,
        project: KProject,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a team cascades to project teams but not the project."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_team)
        await session.commit()

        # Delete the team
        await session.delete(team)
        await session.commit()

        # Verify project team is deleted
        result_exec = await session.execute(
            select(KProjectTeam).where(KProjectTeam.team_id == team.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify project still exists
        await session.refresh(project)
        assert project.id == project.id
