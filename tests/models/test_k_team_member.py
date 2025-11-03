"""Unit tests for KTeamMember model."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from app.models.k_principal import KPrincipal
from app.models.k_team import KTeam
from app.models.k_team_member import KTeamMember


class TestKTeamMemberModel:
    """Test suite for KTeamMember model."""

    @pytest.fixture
    def team(self, session: Session, creator_id: UUID) -> KTeam:
        """Create a test team."""
        team = KTeam(
            name="Engineering",
            scope="global",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team)
        session.commit()
        session.refresh(team)
        return team

    @pytest.fixture
    def principal(self, session: Session, creator_id: UUID) -> KPrincipal:
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
        session.commit()
        session.refresh(principal)
        return principal

    def test_create_team_member_with_required_fields(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test creating a team member with only required fields."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()
        session.refresh(team_member)

        assert team_member.team_id == team.id
        assert team_member.principal_id == principal.id
        assert team_member.scope == "global"

    def test_team_member_default_values(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test that default values are set correctly."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()
        session.refresh(team_member)

        assert team_member.role is None
        assert team_member.meta == {}
        assert isinstance(team_member.created, datetime)
        assert isinstance(team_member.last_modified, datetime)

    def test_team_member_with_role(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test creating a team member with a role."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()
        session.refresh(team_member)

        assert team_member.role == "admin"

    def test_team_member_with_meta_data(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test creating a team member with metadata."""
        meta_data = {
            "join_date": "2024-01-01",
            "department": "Backend",
            "level": "Senior",
        }

        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            role="developer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()
        session.refresh(team_member)

        assert team_member.meta == meta_data
        assert team_member.meta["department"] == "Backend"
        assert team_member.meta["level"] == "Senior"

    def test_team_member_composite_primary_key(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test that team_id + principal_id form a composite primary key."""
        team_member1 = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member1)
        session.commit()

        # Try to create another membership with same team_id + principal_id
        team_member2 = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            role="different_role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member2)
        with pytest.raises(Exception):  # Should raise IntegrityError
            session.commit()

    def test_principal_multiple_teams(
        self, session: Session, principal: KPrincipal, creator_id: UUID
    ):
        """Test that a principal can be a member of multiple teams."""
        team1 = KTeam(
            name="Engineering",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        team2 = KTeam(
            name="Product",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team1)
        session.add(team2)
        session.commit()

        member1 = KTeamMember(
            team_id=team1.id,
            principal_id=principal.id,
            scope="global",
            role="developer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member2 = KTeamMember(
            team_id=team2.id,
            principal_id=principal.id,
            scope="global",
            role="contributor",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.add(member2)
        session.commit()

        # Query all teams for this principal
        memberships = session.exec(
            select(KTeamMember).where(KTeamMember.principal_id == principal.id)
        ).all()

        assert len(memberships) == 2
        roles = {m.role for m in memberships}
        assert roles == {"developer", "contributor"}

    def test_team_multiple_members(
        self, session: Session, team: KTeam, creator_id: UUID
    ):
        """Test that a team can have multiple members."""
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
        session.commit()

        member1 = KTeamMember(
            team_id=team.id,
            principal_id=principal1.id,
            scope="global",
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member2 = KTeamMember(
            team_id=team.id,
            principal_id=principal2.id,
            scope="global",
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.add(member2)
        session.commit()

        # Query all members of this team
        members = session.exec(
            select(KTeamMember).where(KTeamMember.team_id == team.id)
        ).all()

        assert len(members) == 2
        roles = {m.role for m in members}
        assert roles == {"admin", "member"}

    def test_team_member_query_by_role(
        self, session: Session, team: KTeam, creator_id: UUID
    ):
        """Test querying team members by role."""
        principals = []
        for i in range(3):
            principal = KPrincipal(
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name=f"User",
                last_name=f"{i}",
                display_name=f"User {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            principals.append(principal)
            session.add(principal)

        session.commit()

        # Add members with different roles
        member1 = KTeamMember(
            team_id=team.id,
            principal_id=principals[0].id,
            scope="global",
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member2 = KTeamMember(
            team_id=team.id,
            principal_id=principals[1].id,
            scope="global",
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member3 = KTeamMember(
            team_id=team.id,
            principal_id=principals[2].id,
            scope="global",
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.add(member2)
        session.add(member3)
        session.commit()

        # Query admins
        admins = session.exec(
            select(KTeamMember).where(
                KTeamMember.team_id == team.id,
                KTeamMember.role == "admin",
            )
        ).all()

        assert len(admins) == 2

    def test_team_member_update(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test updating team member fields."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()

        # Update role
        team_member.role = "admin"
        team_member.meta = {"promoted": True}
        session.add(team_member)
        session.commit()
        session.refresh(team_member)

        assert team_member.role == "admin"
        assert team_member.meta == {"promoted": True}

    def test_team_member_delete(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test deleting a team member."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()

        # Delete the team member
        session.delete(team_member)
        session.commit()

        # Verify it's deleted
        result = session.exec(
            select(KTeamMember).where(
                KTeamMember.team_id == team.id,
                KTeamMember.principal_id == principal.id,
            )
        ).first()
        assert result is None

    def test_cascade_delete_team(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test that deleting a team cascades to team members."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()

        # Delete the team
        session.delete(team)
        session.commit()

        # Verify team member is also deleted
        result = session.exec(
            select(KTeamMember).where(KTeamMember.team_id == team.id)
        ).first()
        assert result is None

    def test_team_member_meta_json_field(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test that meta field correctly stores and retrieves JSON data."""
        meta_data = {
            "permissions": ["read", "write", "delete"],
            "settings": {
                "notifications": True,
                "auto_assign": False,
            },
            "stats": {
                "tasks_completed": 42,
                "reviews_done": 15,
            },
        }

        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            role="developer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        session.commit()
        session.refresh(team_member)

        assert team_member.meta == meta_data
        assert team_member.meta["permissions"] == ["read", "write", "delete"]
        assert team_member.meta["settings"]["notifications"] is True
        assert team_member.meta["stats"]["tasks_completed"] == 42

    def test_team_member_scope_field(
        self, session: Session, team: KTeam, principal: KPrincipal, creator_id: UUID
    ):
        """Test that team members can have different scopes."""
        member1 = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="global",
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.commit()

        # Create another team and add the same principal with different scope
        team2 = KTeam(
            name="Product",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team2)
        session.commit()

        member2 = KTeamMember(
            team_id=team2.id,
            principal_id=principal.id,
            scope="tenant1",
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member2)
        session.commit()

        # Verify different scopes
        memberships = session.exec(
            select(KTeamMember).where(KTeamMember.principal_id == principal.id)
        ).all()

        assert len(memberships) == 2
        scopes = {m.scope for m in memberships}
        assert scopes == {"global", "tenant1"}

    def test_team_member_count(self, session: Session, team: KTeam, creator_id: UUID):
        """Test counting team members."""
        principals = []
        for i in range(5):
            principal = KPrincipal(
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name=f"User",
                last_name=f"{i}",
                display_name=f"User {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            principals.append(principal)
            session.add(principal)

        session.commit()

        # Add all principals to the team
        for principal in principals:
            member = KTeamMember(
                team_id=team.id,
                principal_id=principal.id,
                scope="global",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(member)

        session.commit()

        # Count members
        members = session.exec(
            select(KTeamMember).where(KTeamMember.team_id == team.id)
        ).all()

        assert len(members) == 5
