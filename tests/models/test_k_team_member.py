"""Unit tests for KTeamMember model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_principal import KPrincipal
from app.models.k_team import KTeam
from app.models.k_team_member import KTeamMember


class TestKTeamMemberModel:
    """Test suite for KTeamMember model."""

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
    async def test_create_team_member_with_required_fields(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a team member with only required fields."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()
        await session.refresh(team_member)

        assert team_member.team_id == team.id
        assert team_member.principal_id == principal.id
        assert team_member.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_team_member_default_values(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()
        await session.refresh(team_member)

        assert team_member.role is None
        assert team_member.meta == {}
        assert isinstance(team_member.created, datetime)
        assert isinstance(team_member.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_team_member_with_role(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a team member with a role."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()
        await session.refresh(team_member)

        assert team_member.role == "admin"

    @pytest.mark.asyncio
    async def test_team_member_with_meta_data(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
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
            org_id=test_org_id,
            role="developer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()
        await session.refresh(team_member)

        assert team_member.meta == meta_data
        assert team_member.meta["department"] == "Backend"
        assert team_member.meta["level"] == "Senior"

    @pytest.mark.asyncio
    async def test_team_member_composite_primary_key(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that team_id + principal_id form a composite primary key."""
        team_member1 = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(team_member1)

        # Try to create another membership with same team_id + principal_id
        team_member2 = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="different_role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member2)
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
        """Test that a principal can be a member of multiple teams."""
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

        member1 = KTeamMember(
            team_id=team1.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="developer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member2 = KTeamMember(
            team_id=team2.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="contributor",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.add(member2)
        await session.commit()

        # Query all teams for this principal
        result_exec = await session.execute(
            select(KTeamMember).where(KTeamMember.principal_id == principal.id)
        )
        memberships = result_exec.scalars().all()

        assert len(memberships) == 2
        roles = {m.role for m in memberships}
        assert roles == {"developer", "contributor"}

    @pytest.mark.asyncio
    async def test_team_multiple_members(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
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
        await session.commit()

        member1 = KTeamMember(
            team_id=team.id,
            principal_id=principal1.id,
            org_id=test_org_id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member2 = KTeamMember(
            team_id=team.id,
            principal_id=principal2.id,
            org_id=test_org_id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.add(member2)
        await session.commit()

        # Query all members of this team
        result_exec = await session.execute(
            select(KTeamMember).where(KTeamMember.team_id == team.id)
        )
        members = result_exec.scalars().all()

        assert len(members) == 2
        roles = {m.role for m in members}
        assert roles == {"admin", "member"}

    @pytest.mark.asyncio
    async def test_team_member_query_by_role(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying team members by role."""
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

        # Add members with different roles
        member1 = KTeamMember(
            team_id=team.id,
            principal_id=principals[0].id,
            org_id=test_org_id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member2 = KTeamMember(
            team_id=team.id,
            principal_id=principals[1].id,
            org_id=test_org_id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        member3 = KTeamMember(
            team_id=team.id,
            principal_id=principals[2].id,
            org_id=test_org_id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        session.add(member2)
        session.add(member3)
        await session.commit()

        # Query admins
        result_exec = await session.execute(
            select(KTeamMember).where(
                KTeamMember.team_id == team.id,
                KTeamMember.role == "admin",
            )
        )
        admins = result_exec.scalars().all()

        assert len(admins) == 2

    @pytest.mark.asyncio
    async def test_team_member_update(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test updating team member fields."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()

        # Update role
        team_member.role = "admin"
        team_member.meta = {"promoted": True}
        session.add(team_member)
        await session.commit()
        await session.refresh(team_member)

        assert team_member.role == "admin"
        assert team_member.meta == {"promoted": True}

    @pytest.mark.asyncio
    async def test_team_member_delete(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test deleting a team member."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()

        # Delete the team member
        await session.delete(team_member)
        await session.commit()

        # Verify it's deleted
        result_exec = await session.execute(
            select(KTeamMember).where(
                KTeamMember.team_id == team.id,
                KTeamMember.principal_id == principal.id,
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
        """Test that deleting a team cascades to team members but not the principal."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()

        # Delete the team
        await session.delete(team)
        await session.commit()

        # Verify team member is also deleted
        result_exec = await session.execute(
            select(KTeamMember).where(KTeamMember.team_id == team.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify principal still exists
        await session.refresh(principal)
        assert principal.id == principal.id

    @pytest.mark.asyncio
    async def test_cascade_delete_principal(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a principal cascades to team members but not the team."""
        team_member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()

        # Delete the principal
        await session.delete(principal)
        await session.commit()

        # Verify team member is also deleted
        result_exec = await session.execute(
            select(KTeamMember).where(KTeamMember.principal_id == principal.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify team still exists
        await session.refresh(team)
        assert team.id == team.id

    @pytest.mark.asyncio
    async def test_team_member_meta_json_field(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
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
            org_id=test_org_id,
            role="developer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(team_member)
        await session.commit()
        await session.refresh(team_member)

        assert team_member.meta == meta_data
        assert team_member.meta["permissions"] == ["read", "write", "delete"]
        assert team_member.meta["settings"]["notifications"] is True
        assert team_member.meta["stats"]["tasks_completed"] == 42

    @pytest.mark.asyncio
    async def test_team_member_scope_field(
        self,
        session: AsyncSession,
        team: KTeam,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that team members can have different org_ids."""
        from app.models import KOrganization

        # Create two organizations
        org1 = KOrganization(
            name="Organization 1",
            alias="org1_member_scope",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        org2 = KOrganization(
            name="Organization 2",
            alias="org2_member_scope",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add_all([org1, org2])
        await session.commit()
        await session.refresh(org1)
        await session.refresh(org2)

        member1 = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=org1.id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member1)
        await session.commit()

        # Create another team and add the same principal with different org_id
        team2 = KTeam(
            name="Product",
            org_id=org2.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team2)
        await session.commit()

        member2 = KTeamMember(
            team_id=team2.id,
            principal_id=principal.id,
            org_id=org2.id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(member2)
        await session.commit()

        # Verify different org_ids
        result_exec = await session.execute(
            select(KTeamMember).where(KTeamMember.principal_id == principal.id)
        )
        memberships = result_exec.scalars().all()

        assert len(memberships) == 2
        org_ids = {m.org_id for m in memberships}
        assert org_ids == {org1.id, org2.id}

    @pytest.mark.asyncio
    async def test_team_member_count(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ):
        """Test counting team members."""
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

        # Add all principals to the team
        for principal in principals:
            member = KTeamMember(
                team_id=team.id,
                principal_id=principal.id,
                org_id=test_org_id,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(member)

        await session.commit()

        # Count members
        result_exec = await session.execute(
            select(KTeamMember).where(KTeamMember.team_id == team.id)
        )
        members = result_exec.scalars().all()

        assert len(members) == 5
