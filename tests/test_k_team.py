"""Unit tests for KTeam model."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from app.models.k_team import KTeam


class TestKTeamModel:
    """Test suite for KTeam model."""

    def test_create_team_with_required_fields(self, session: Session, creator_id: UUID):
        """Test creating a team with only required fields."""
        team = KTeam(
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.id is not None
        assert isinstance(team.id, UUID)
        assert team.name == "Engineering"

    def test_team_default_values(self, session: Session, creator_id: UUID):
        """Test that default values are set correctly."""
        team = KTeam(
            name="Marketing",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.scope == "global"
        assert team.meta == {}
        assert isinstance(team.created, datetime)
        assert isinstance(team.last_modified, datetime)

    def test_team_with_custom_scope(self, session: Session, creator_id: UUID):
        """Test creating a team with a custom scope."""
        team = KTeam(
            scope="tenant1",
            name="Sales",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.scope == "tenant1"
        assert team.name == "Sales"

    def test_team_with_meta_data(self, session: Session, creator_id: UUID):
        """Test creating a team with metadata."""
        meta_data = {
            "department": "Engineering",
            "location": "San Francisco",
            "budget": 1000000,
        }

        team = KTeam(
            name="Backend Team",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.meta == meta_data
        assert team.meta["department"] == "Engineering"
        assert team.meta["location"] == "San Francisco"
        assert team.meta["budget"] == 1000000

    def test_team_unique_constraint(self, session: Session, creator_id: UUID):
        """Test that scope+name combination must be unique."""
        team1 = KTeam(
            scope="global",
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team1)
        session.commit()

        # Try to create another team with same scope+name
        team2 = KTeam(
            scope="global",
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team2)
        with pytest.raises(Exception):  # Should raise IntegrityError
            session.commit()

    def test_team_same_name_different_scope(self, session: Session, creator_id: UUID):
        """Test that same team name can exist in different scopes."""
        team1 = KTeam(
            scope="tenant1",
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        team2 = KTeam(
            scope="tenant2",
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team1)
        session.add(team2)
        session.commit()

        # Both should exist
        teams = session.exec(select(KTeam)).all()
        assert len(teams) == 2

    def test_team_query(self, session: Session, creator_id: UUID):
        """Test querying teams from database."""
        team = KTeam(
            name="Product Team",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()

        # Query by name
        result = session.exec(
            select(KTeam).where(KTeam.name == "Product Team")
        ).first()

        assert result is not None
        assert result.name == "Product Team"

    def test_team_query_by_scope(self, session: Session, creator_id: UUID):
        """Test querying teams by scope."""
        team1 = KTeam(
            scope="tenant1",
            name="Team A",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        team2 = KTeam(
            scope="tenant1",
            name="Team B",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        team3 = KTeam(
            scope="tenant2",
            name="Team C",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team1)
        session.add(team2)
        session.add(team3)
        session.commit()

        # Query teams in tenant1
        results = session.exec(
            select(KTeam).where(KTeam.scope == "tenant1")
        ).all()

        assert len(results) == 2
        team_names = {t.name for t in results}
        assert team_names == {"Team A", "Team B"}

    def test_team_update(self, session: Session, creator_id: UUID):
        """Test updating team fields."""
        team = KTeam(
            name="Old Name",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        # Update fields
        team.name = "New Name"
        team.meta = {"updated": True}
        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.name == "New Name"
        assert team.meta == {"updated": True}

    def test_team_delete(self, session: Session, creator_id: UUID):
        """Test deleting a team."""
        team = KTeam(
            name="To Delete",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        team_id = team.id

        # Delete the team
        session.delete(team)
        session.commit()

        # Verify it's deleted
        result = session.get(KTeam, team_id)
        assert result is None

    def test_team_meta_json_field(self, session: Session, creator_id: UUID):
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
            name="Complex Meta Team",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.meta == meta_data
        assert team.meta["description"] == "A team for backend development"
        assert team.meta["settings"]["notifications"] is True
        assert team.meta["tags"] == ["backend", "api", "microservices"]
        assert team.meta["metrics"]["members_count"] == 10

    def test_team_list_all(self, session: Session, creator_id: UUID):
        """Test listing all teams."""
        teams_data = [
            {"name": "Team 1", "scope": "global"},
            {"name": "Team 2", "scope": "tenant1"},
            {"name": "Team 3", "scope": "tenant2"},
        ]

        for team_data in teams_data:
            team = KTeam(
                **team_data,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(team)

        session.commit()

        # List all teams
        all_teams = session.exec(select(KTeam)).all()
        assert len(all_teams) == 3

    def test_team_count_by_scope(self, session: Session, creator_id: UUID):
        """Test counting teams by scope."""
        # Create teams in different scopes
        for i in range(3):
            team = KTeam(
                scope="tenant1",
                name=f"Team {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(team)

        for i in range(2):
            team = KTeam(
                scope="tenant2",
                name=f"Team {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(team)

        session.commit()

        # Count teams in tenant1
        tenant1_teams = session.exec(
            select(KTeam).where(KTeam.scope == "tenant1")
        ).all()
        assert len(tenant1_teams) == 3

        # Count teams in tenant2
        tenant2_teams = session.exec(
            select(KTeam).where(KTeam.scope == "tenant2")
        ).all()
        assert len(tenant2_teams) == 2

    def test_team_empty_meta(self, session: Session, creator_id: UUID):
        """Test that teams can have empty meta dictionaries."""
        team = KTeam(
            name="Empty Meta Team",
            meta={},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team)
        session.commit()
        session.refresh(team)

        assert team.meta == {}
        assert len(team.meta) == 0
