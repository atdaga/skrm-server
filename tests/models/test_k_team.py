"""Unit tests for KTeam model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_team import KTeam


class TestKTeamModel:
    """Test suite for KTeam model."""

    @pytest.mark.asyncio
    async def test_create_team_with_required_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a team with only required fields."""
        team = KTeam(
            org_id=test_org_id,
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.id is not None
        assert isinstance(team.id, UUID)
        assert team.name == "Engineering"

    @pytest.mark.asyncio
    async def test_team_default_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that default values are set correctly."""
        team = KTeam(
            org_id=test_org_id,
            name="Marketing",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.org_id == test_org_id
        assert team.meta == {}
        assert isinstance(team.created, datetime)
        assert isinstance(team.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_team_with_custom_scope(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a team with a custom org_id."""
        team = KTeam(
            org_id=test_org_id,
            name="Sales",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.org_id == test_org_id
        assert team.name == "Sales"

    @pytest.mark.asyncio
    async def test_team_with_meta_data(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a team with metadata."""
        meta_data = {
            "department": "Engineering",
            "location": "San Francisco",
            "budget": 1000000,
        }

        team = KTeam(
            org_id=test_org_id,
            name="Backend Team",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.meta == meta_data
        assert team.meta["department"] == "Engineering"
        assert team.meta["location"] == "San Francisco"
        assert team.meta["budget"] == 1000000

    @pytest.mark.asyncio
    async def test_team_unique_constraint(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that org_id+name combination must be unique."""
        team1 = KTeam(
            org_id=test_org_id,
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team1)
        await session.commit()

        # Try to create another team with same org_id+name
        team2 = KTeam(
            org_id=test_org_id,
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_team_same_name_different_scope(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that same team name can exist in different org_ids."""
        from app.models import KOrganization

        # Create two organizations
        org1 = KOrganization(
            name="Organization 1",
            alias="org1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        org2 = KOrganization(
            name="Organization 2",
            alias="org2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add_all([org1, org2])
        await session.commit()
        await session.refresh(org1)
        await session.refresh(org2)

        team1 = KTeam(
            org_id=org1.id,
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        team2 = KTeam(
            org_id=org2.id,
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team1)
        session.add(team2)
        await session.commit()

        # Both should exist
        result_exec = await session.execute(
            select(KTeam).where(KTeam.deleted == False)  # type: ignore[comparison-overlap]  # noqa: E712
        )
        teams = result_exec.scalars().all()
        assert len(teams) == 2

    @pytest.mark.asyncio
    async def test_team_query(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying teams from database."""
        team = KTeam(
            org_id=test_org_id,
            name="Product Team",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()

        # Query by name
        result_exec = await session.execute(
            select(KTeam).where(
                KTeam.name == "Product Team",
                KTeam.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        result = result_exec.scalar_one_or_none()

        assert result is not None
        assert result.name == "Product Team"

    @pytest.mark.asyncio
    async def test_team_query_by_scope(self, session: AsyncSession, creator_id: UUID):
        """Test querying teams by org_id."""
        from app.models import KOrganization

        # Create two organizations
        org1 = KOrganization(
            name="Organization 1",
            alias="org1_query",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        org2 = KOrganization(
            name="Organization 2",
            alias="org2_query",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add_all([org1, org2])
        await session.commit()
        await session.refresh(org1)
        await session.refresh(org2)

        team1 = KTeam(
            org_id=org1.id,
            name="Team A",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        team2 = KTeam(
            org_id=org1.id,
            name="Team B",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        team3 = KTeam(
            org_id=org2.id,
            name="Team C",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team1)
        session.add(team2)
        session.add(team3)
        await session.commit()

        # Query teams in org_id_1
        result_exec = await session.execute(
            select(KTeam).where(
                KTeam.org_id == org1.id,
                KTeam.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        results = result_exec.scalars().all()

        assert len(results) == 2
        team_names = {t.name for t in results}
        assert team_names == {"Team A", "Team B"}

    @pytest.mark.asyncio
    async def test_team_update(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test updating team fields."""
        team = KTeam(
            org_id=test_org_id,
            name="Old Name",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        # Update fields
        team.name = "New Name"
        team.meta = {"updated": True}
        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.name == "New Name"
        assert team.meta == {"updated": True}

    @pytest.mark.asyncio
    async def test_team_delete(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test deleting a team."""
        team = KTeam(
            org_id=test_org_id,
            name="To Delete",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        team_id = team.id

        # Delete the team
        await session.delete(team)
        await session.commit()

        # Verify it's deleted
        result = await session.get(KTeam, team_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_team_meta_json_field(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that meta field correctly stores and retrieves complex JSON data."""
        meta_data = {
            "description": "A team for backend development",
            "settings": {
                "notifications": True,
                "auto_assign": False,
            },
            "tags": ["backend", "api", "microservices"],
            "metrics": {
                "members_count": 10,
                "projects_count": 5,
            },
        }

        team = KTeam(
            org_id=test_org_id,
            name="Complex Meta Team",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.meta == meta_data
        assert team.meta["description"] == "A team for backend development"
        assert team.meta["settings"]["notifications"] is True
        assert team.meta["tags"] == ["backend", "api", "microservices"]
        assert team.meta["metrics"]["members_count"] == 10

    @pytest.mark.asyncio
    async def test_team_list_all(self, session: AsyncSession, creator_id: UUID):
        """Test listing all teams."""
        from app.models import KOrganization

        # Create three organizations
        orgs = []
        for i in range(3):
            org = KOrganization(
                name=f"Organization {i+1}",
                alias=f"org{i+1}_list",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            orgs.append(org)
            session.add(org)
        await session.commit()
        for org in orgs:
            await session.refresh(org)

        teams_data = [
            {"name": "Team 1", "org_id": orgs[0].id},
            {"name": "Team 2", "org_id": orgs[1].id},
            {"name": "Team 3", "org_id": orgs[2].id},
        ]

        for team_data in teams_data:
            team = KTeam(
                **team_data,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(team)

        await session.commit()

        # List all teams
        result_exec = await session.execute(
            select(KTeam).where(KTeam.deleted == False)  # type: ignore[comparison-overlap]  # noqa: E712
        )
        all_teams = result_exec.scalars().all()
        assert len(all_teams) == 3

    @pytest.mark.asyncio
    async def test_team_count_by_scope(self, session: AsyncSession, creator_id: UUID):
        """Test counting teams by org_id."""
        from app.models import KOrganization

        # Create two organizations
        org1 = KOrganization(
            name="Organization 1",
            alias="org1_count",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        org2 = KOrganization(
            name="Organization 2",
            alias="org2_count",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add_all([org1, org2])
        await session.commit()
        await session.refresh(org1)
        await session.refresh(org2)

        # Create teams in different org_ids
        for i in range(3):
            team = KTeam(
                org_id=org1.id,
                name=f"Org1 Team {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(team)

        for i in range(2):
            team = KTeam(
                org_id=org2.id,
                name=f"Org2 Team {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(team)

        await session.commit()

        # Count teams in org_id_1
        result_exec = await session.execute(
            select(KTeam).where(
                KTeam.org_id == org1.id,
                KTeam.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        org1_teams = result_exec.scalars().all()
        assert len(org1_teams) == 3

        # Count teams in org_id_2
        result_exec = await session.execute(
            select(KTeam).where(
                KTeam.org_id == org2.id,
                KTeam.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        org2_teams = result_exec.scalars().all()
        assert len(org2_teams) == 2

    @pytest.mark.asyncio
    async def test_team_empty_meta(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that teams can have empty meta dictionaries."""
        team = KTeam(
            org_id=test_org_id,
            name="Empty Meta Team",
            meta={},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        await session.commit()
        await session.refresh(team)

        assert team.meta == {}
        assert len(team.meta) == 0
