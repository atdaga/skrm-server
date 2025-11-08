"""Unit tests for team member management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KPrincipal, KTeam, KTeamMember
from app.routes.v1.team_members import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with team_members router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


@pytest.fixture
async def team(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KTeam:
    """Create a test team."""
    team = KTeam(
        name="Engineering Team",
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(team)
    await async_session.commit()
    await async_session.refresh(team)
    return team


class TestAddTeamMember:
    """Test suite for POST /teams/{team_id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_add_team_member_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new team member."""
        member_data = {
            "principal_id": str(principal.id),
            "role": "developer",
            "meta": {"department": "Backend", "level": "Senior"},
        }

        response = await client.post(f"/teams/{team.id}/members", json=member_data)

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "developer"
        assert data["meta"] == {"department": "Backend", "level": "Senior"}
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_add_team_member_minimal_data(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        test_org_id: UUID,
    ):
        """Test adding a team member with minimal required fields."""
        member_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/teams/{team.id}/members", json=member_data)

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_team_member_duplicate(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test that adding a duplicate team member fails."""
        # Add member directly in database
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()
        async_session.expunge(member)

        # Try to add same member via API
        member_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/teams/{team.id}/members", json=member_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_team_member_team_not_found(
        self,
        client: AsyncClient,
        principal: KPrincipal,
    ):
        """Test adding a member to a non-existent team."""
        non_existent_team_id = uuid7()
        member_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/teams/{non_existent_team_id}/members", json=member_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_team_member_with_role(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
    ):
        """Test adding a team member with a specific role."""
        member_data = {"principal_id": str(principal.id), "role": "lead"}

        response = await client.post(f"/teams/{team.id}/members", json=member_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "lead"

    @pytest.mark.asyncio
    async def test_add_team_member_with_complex_meta(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
    ):
        """Test adding a team member with complex metadata."""
        member_data = {
            "principal_id": str(principal.id),
            "role": "developer",
            "meta": {
                "skills": ["Python", "FastAPI", "SQLAlchemy"],
                "certifications": {"aws": True, "gcp": False},
                "performance": {"rating": 4.5, "reviews": 12},
            },
        }

        response = await client.post(f"/teams/{team.id}/members", json=member_data)

        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == member_data["meta"]


class TestListTeamMembers:
    """Test suite for GET /teams/{team_id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_list_team_members_empty(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test listing team members when none exist."""
        response = await client.get(f"/teams/{team.id}/members")

        assert response.status_code == 200
        data = response.json()
        assert data["members"] == []

    @pytest.mark.asyncio
    async def test_list_team_members_single(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing team members with a single member."""
        # Add a member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="developer",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/members")

        assert response.status_code == 200
        data = response.json()
        assert len(data["members"]) == 1
        assert data["members"][0]["team_id"] == str(team.id)
        assert data["members"][0]["principal_id"] == str(principal.id)
        assert data["members"][0]["role"] == "developer"

    @pytest.mark.asyncio
    async def test_list_team_members_multiple(
        self,
        client: AsyncClient,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple team members."""
        # Create multiple principals and add as members
        principals_data = [
            {"username": "user1", "email": "user1@example.com", "role": "admin"},
            {"username": "user2", "email": "user2@example.com", "role": "developer"},
            {"username": "user3", "email": "user3@example.com", "role": "designer"},
        ]

        for idx, p_data in enumerate(principals_data):
            principal = KPrincipal(
                username=p_data["username"],
                primary_email=p_data["email"],
                first_name="User",
                last_name=str(idx),
                display_name=f"User {idx}",
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(principal)
            await async_session.commit()
            await async_session.refresh(principal)

            member = KTeamMember(
                team_id=team.id,
                principal_id=principal.id,
                org_id=test_org_id,
                role=p_data["role"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(member)

        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/members")

        assert response.status_code == 200
        data = response.json()
        assert len(data["members"]) == 3
        roles = {m["role"] for m in data["members"]}
        assert roles == {"admin", "developer", "designer"}

    @pytest.mark.asyncio
    async def test_list_team_members_team_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing members of a non-existent team."""
        non_existent_team_id = uuid7()

        response = await client.get(f"/teams/{non_existent_team_id}/members")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetTeamMember:
    """Test suite for GET /teams/{team_id}/members/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_team_member_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully getting a single team member."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="developer",
            meta={"level": "senior"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/members/{principal.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "developer"
        assert data["meta"] == {"level": "senior"}

    @pytest.mark.asyncio
    async def test_get_team_member_not_found(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test getting a team member that doesn't exist."""
        non_existent_principal_id = uuid7()

        response = await client.get(
            f"/teams/{team.id}/members/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateTeamMember:
    """Test suite for PATCH /teams/{team_id}/members/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_team_member_role(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating a team member's role."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="developer",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        update_data = {"role": "lead"}

        response = await client.patch(
            f"/teams/{team.id}/members/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "lead"
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)

    @pytest.mark.asyncio
    async def test_update_team_member_meta(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating a team member's metadata."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        update_data = {"meta": {"new": "data", "updated": True}}

        response = await client.patch(
            f"/teams/{team.id}/members/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}

    @pytest.mark.asyncio
    async def test_update_team_member_both_fields(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating both role and meta."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="developer",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        update_data = {"role": "senior_developer", "meta": {"new": "data"}}

        response = await client.patch(
            f"/teams/{team.id}/members/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "senior_developer"
        assert data["meta"] == {"new": "data"}

    @pytest.mark.asyncio
    async def test_update_team_member_not_found(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test updating a team member that doesn't exist."""
        non_existent_principal_id = uuid7()
        update_data = {"role": "lead"}

        response = await client.patch(
            f"/teams/{team.id}/members/{non_existent_principal_id}", json=update_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_team_member_empty_payload(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="developer",
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        update_data = {}

        response = await client.patch(
            f"/teams/{team.id}/members/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "developer"
        assert data["meta"] == {"key": "value"}


class TestRemoveTeamMember:
    """Test suite for DELETE /teams/{team_id}/members/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_team_member_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a team member."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        response = await client.delete(f"/teams/{team.id}/members/{principal.id}")

        assert response.status_code == 204
        assert response.content == b""

        # Verify member is actually deleted
        from sqlmodel import select

        result = await async_session.execute(
            select(KTeamMember).where(
                KTeamMember.team_id == team.id,
                KTeamMember.principal_id == principal.id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_team_member_not_found(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test removing a team member that doesn't exist."""
        non_existent_principal_id = uuid7()

        response = await client.delete(
            f"/teams/{team.id}/members/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
