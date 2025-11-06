"""Unit tests for KTeamReviewer model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_principal import KPrincipal
from app.models.k_team import KTeam
from app.models.k_team_reviewer import KTeamReviewer


class TestKTeamReviewerModel:
    """Test suite for KTeamReviewer model."""

    @pytest.fixture
    async def team(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KTeam:
        """Create a test team."""
        team = KTeam(
            name="Engineering",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team)
        await session.commit()
        await session.refresh(team)
        return team

    @pytest.fixture
    async def principal(self, session: AsyncSession, creator_id: UUID) -> KPrincipal:
        """Create a test principal."""
        principal = KPrincipal(
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(principal)
        await session.commit()
        await session.refresh(principal)
        return principal

    @pytest.mark.asyncio
    async def test_create_team_reviewer_with_required_fields(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a team reviewer with only required fields."""
        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()
        await session.refresh(team_reviewer)

        assert team_reviewer.team_id == team.id
        assert team_reviewer.principal_id == principal.id
        assert team_reviewer.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_team_reviewer_default_values(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()
        await session.refresh(team_reviewer)

        assert team_reviewer.role is None
        assert team_reviewer.meta == {}
        assert isinstance(team_reviewer.created, datetime)
        assert isinstance(team_reviewer.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_team_reviewer_with_role(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a team reviewer with a role."""
        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead_reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()
        await session.refresh(team_reviewer)

        assert team_reviewer.role == "lead_reviewer"

    @pytest.mark.asyncio
    async def test_team_reviewer_with_meta_data(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a team reviewer with metadata."""
        meta_data = {
            "specialization": "security",
            "review_count": 42,
            "languages": ["python", "go"],
        }

        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="reviewer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()
        await session.refresh(team_reviewer)

        assert team_reviewer.meta == meta_data
        assert team_reviewer.meta["specialization"] == "security"
        assert team_reviewer.meta["review_count"] == 42

    @pytest.mark.asyncio
    async def test_team_reviewer_composite_primary_key(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that team_id + principal_id form a composite primary key."""
        team_reviewer1 = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(team_reviewer1)

        # Try to create another reviewer assignment with same team_id + principal_id
        team_reviewer2 = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="different_role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_principal_multiple_teams(
        self,
        session: AsyncSession,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that a principal can be a reviewer of multiple teams."""
        team1 = KTeam(
            name="Engineering",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        team2 = KTeam(
            name="Product",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team1)
        session.add(team2)
        await session.commit()

        reviewer1 = KTeamReviewer(
            team_id=team1.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead_reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        reviewer2 = KTeamReviewer(
            team_id=team2.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(reviewer1)
        session.add(reviewer2)
        await session.commit()

        # Query all teams for this principal as reviewer
        result_exec = await session.execute(
            select(KTeamReviewer).where(KTeamReviewer.principal_id == principal.id)
        )
        assignments = result_exec.scalars().all()

        assert len(assignments) == 2
        roles = {r.role for r in assignments}
        assert roles == {"lead_reviewer", "reviewer"}

    @pytest.mark.asyncio
    async def test_team_multiple_reviewers(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ):
        """Test that a team can have multiple reviewers."""
        principal1 = KPrincipal(
            username="user1",
            primary_email="user1@example.com",
            first_name="User",
            last_name="One",
            display_name="User One",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        principal2 = KPrincipal(
            username="user2",
            primary_email="user2@example.com",
            first_name="User",
            last_name="Two",
            display_name="User Two",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal1)
        session.add(principal2)
        await session.commit()

        reviewer1 = KTeamReviewer(
            team_id=team.id,
            principal_id=principal1.id,
            org_id=test_org_id,
            role="lead_reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        reviewer2 = KTeamReviewer(
            team_id=team.id,
            principal_id=principal2.id,
            org_id=test_org_id,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(reviewer1)
        session.add(reviewer2)
        await session.commit()

        # Query all reviewers of this team
        result_exec = await session.execute(
            select(KTeamReviewer).where(KTeamReviewer.team_id == team.id)
        )
        reviewers = result_exec.scalars().all()

        assert len(reviewers) == 2
        roles = {r.role for r in reviewers}
        assert roles == {"lead_reviewer", "reviewer"}

    @pytest.mark.asyncio
    async def test_team_reviewer_query_by_role(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying team reviewers by role."""
        principals = []
        for i in range(3):
            principal = KPrincipal(
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name="User",
                last_name=f"{i}",
                display_name=f"User {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            principals.append(principal)
            session.add(principal)

        await session.commit()

        # Add reviewers with different roles
        reviewer1 = KTeamReviewer(
            team_id=team.id,
            principal_id=principals[0].id,
            org_id=test_org_id,
            role="lead_reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        reviewer2 = KTeamReviewer(
            team_id=team.id,
            principal_id=principals[1].id,
            org_id=test_org_id,
            role="lead_reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        reviewer3 = KTeamReviewer(
            team_id=team.id,
            principal_id=principals[2].id,
            org_id=test_org_id,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(reviewer1)
        session.add(reviewer2)
        session.add(reviewer3)
        await session.commit()

        # Query lead reviewers
        result_exec = await session.execute(
            select(KTeamReviewer).where(
                KTeamReviewer.team_id == team.id,
                KTeamReviewer.role == "lead_reviewer",
            )
        )
        lead_reviewers = result_exec.scalars().all()

        assert len(lead_reviewers) == 2

    @pytest.mark.asyncio
    async def test_team_reviewer_update(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test updating team reviewer fields."""
        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()

        # Update role
        team_reviewer.role = "lead_reviewer"
        team_reviewer.meta = {"promoted": True, "promotion_date": "2024-01-01"}
        session.add(team_reviewer)
        await session.commit()
        await session.refresh(team_reviewer)

        assert team_reviewer.role == "lead_reviewer"
        assert team_reviewer.meta == {"promoted": True, "promotion_date": "2024-01-01"}

    @pytest.mark.asyncio
    async def test_team_reviewer_delete(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test deleting a team reviewer."""
        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()

        # Delete the team reviewer
        await session.delete(team_reviewer)
        await session.commit()

        # Verify it's deleted
        result_exec = await session.execute(
            select(KTeamReviewer).where(
                KTeamReviewer.team_id == team.id,
                KTeamReviewer.principal_id == principal.id,
            )
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

    @pytest.mark.asyncio
    async def test_cascade_delete_team(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a team cascades to team reviewers."""
        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()

        # Delete the team
        await session.delete(team)
        await session.commit()

        # Verify team reviewer is also deleted
        result_exec = await session.execute(
            select(KTeamReviewer).where(KTeamReviewer.team_id == team.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

    @pytest.mark.asyncio
    async def test_team_reviewer_meta_json_field(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that meta field correctly stores and retrieves JSON data."""
        meta_data = {
            "specializations": ["security", "performance", "architecture"],
            "settings": {
                "auto_assign": True,
                "notification_enabled": False,
            },
            "stats": {
                "reviews_completed": 156,
                "avg_review_time_hours": 2.5,
            },
        }

        team_reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead_reviewer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_reviewer)
        await session.commit()
        await session.refresh(team_reviewer)

        assert team_reviewer.meta == meta_data
        assert team_reviewer.meta["specializations"] == [
            "security",
            "performance",
            "architecture",
        ]
        assert team_reviewer.meta["settings"]["auto_assign"] is True
        assert team_reviewer.meta["stats"]["reviews_completed"] == 156

    @pytest.mark.asyncio
    async def test_team_reviewer_scope_field(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that team reviewers can have different org_ids."""
        from uuid import uuid4

        org_id_1 = uuid4()
        org_id_2 = uuid4()

        reviewer1 = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=org_id_1,
            role="lead_reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(reviewer1)
        await session.commit()

        # Create another team and add the same principal with different org_id
        team2 = KTeam(
            name="Product",
            org_id=org_id_2,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team2)
        await session.commit()

        reviewer2 = KTeamReviewer(
            team_id=team2.id,
            principal_id=principal.id,
            org_id=org_id_2,
            role="reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(reviewer2)
        await session.commit()

        # Verify different org_ids
        result_exec = await session.execute(
            select(KTeamReviewer).where(KTeamReviewer.principal_id == principal.id)
        )
        assignments = result_exec.scalars().all()

        assert len(assignments) == 2
        org_ids = {r.org_id for r in assignments}
        assert org_ids == {org_id_1, org_id_2}

    @pytest.mark.asyncio
    async def test_team_reviewer_count(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ):
        """Test counting team reviewers."""
        principals = []
        for i in range(5):
            principal = KPrincipal(
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name="User",
                last_name=f"{i}",
                display_name=f"User {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            principals.append(principal)
            session.add(principal)

        await session.commit()

        # Add all principals to the team as reviewers
        for principal in principals:
            reviewer = KTeamReviewer(
                team_id=team.id,
                principal_id=principal.id,
                org_id=test_org_id,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(reviewer)

        await session.commit()

        # Count reviewers
        result_exec = await session.execute(
            select(KTeamReviewer).where(KTeamReviewer.team_id == team.id)
        )
        reviewers = result_exec.scalars().all()

        assert len(reviewers) == 5
