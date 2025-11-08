"""Unit tests for KSprintTeam model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KSprint, KSprintTeam, KTeam


class TestKSprintTeamModel:
    """Test suite for KSprintTeam model."""

    @pytest.fixture
    async def sprint(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KSprint:
        """Create a test sprint."""
        sprint = KSprint(
            org_id=test_org_id,
            title="Test Sprint",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)
        return sprint

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
    async def test_create_sprint_team_with_required_fields(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a sprint team with only required fields."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()
        await session.refresh(sprint_team)

        assert sprint_team.sprint_id == sprint.id
        assert sprint_team.team_id == team.id
        assert sprint_team.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_sprint_team_default_values(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()
        await session.refresh(sprint_team)

        assert sprint_team.role is None
        assert sprint_team.meta == {}
        assert isinstance(sprint_team.created, datetime)
        assert isinstance(sprint_team.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_sprint_team_with_role(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a sprint team with a role."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="development",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()
        await session.refresh(sprint_team)

        assert sprint_team.role == "development"

    @pytest.mark.asyncio
    async def test_sprint_team_with_meta_data(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a sprint team with metadata."""
        meta_data = {
            "capacity": 10,
            "focus_areas": ["backend", "testing"],
            "velocity": 42,
        }

        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="qa",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()
        await session.refresh(sprint_team)

        assert sprint_team.meta == meta_data

    @pytest.mark.asyncio
    async def test_sprint_team_composite_primary_key(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that sprint_id and team_id form a composite primary key."""
        sprint_team1 = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(sprint_team1)

        # Try to create another sprint_team with the same sprint_id and team_id
        sprint_team2 = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_sprint_team_audit_fields(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()
        await session.refresh(sprint_team)

        assert sprint_team.created_by == creator_id
        assert sprint_team.last_modified_by == creator_id

        # Update the sprint team
        sprint_team.role = "lead"
        sprint_team.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(sprint_team)

        assert sprint_team.created_by == creator_id  # Should not change
        assert sprint_team.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_sprint_team_cascade_delete_from_sprint(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a sprint cascades to sprint teams but not the team."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()

        # Delete the sprint
        await session.delete(sprint)
        await session.commit()

        # Verify sprint team is deleted
        result_exec = await session.execute(
            select(KSprintTeam).where(KSprintTeam.sprint_id == sprint.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify team still exists
        await session.refresh(team)
        assert team.id == team.id

    @pytest.mark.asyncio
    async def test_sprint_team_cascade_delete_from_team(
        self,
        session: AsyncSession,
        sprint: KSprint,
        team: KTeam,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a team cascades to sprint teams but not the sprint."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_team)
        await session.commit()

        # Delete the team
        await session.delete(team)
        await session.commit()

        # Verify sprint team is deleted
        result_exec = await session.execute(
            select(KSprintTeam).where(KSprintTeam.team_id == team.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify sprint still exists
        await session.refresh(sprint)
        assert sprint.id == sprint.id
