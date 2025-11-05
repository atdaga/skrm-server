"""Unit tests for team member management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KPrincipal, KTeam, KTeamMember
from app.routes.deps import get_current_token
from app.routes.v1.team_members import router
from app.schemas.user import TokenData


@pytest.fixture
def app_with_overrides(
    async_session: AsyncSession, mock_token_data: TokenData
) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    async def override_get_db():
        yield async_session

    async def override_get_current_token():
        return mock_token_data

    from app.core.db.database import get_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_token] = override_get_current_token

    return app


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def team(
    async_session: AsyncSession, test_scope: str, test_user_id: UUID
) -> KTeam:
    """Create a test team."""
    team = KTeam(
        name="Engineering Team",
        scope=test_scope,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(team)
    await async_session.commit()
    await async_session.refresh(team)
    return team


@pytest.fixture
async def principal(async_session: AsyncSession, test_user_id: UUID) -> KPrincipal:
    """Create a test principal."""
    principal = KPrincipal(
        username="testuser",
        primary_email="test@example.com",
        first_name="Test",
        last_name="User",
        display_name="Test User",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()
    await async_session.refresh(principal)
    return principal


class TestAddTeamMember:
    """Test suite for POST /teams/{team_id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_add_team_member_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        test_scope: str,
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
        assert data["scope"] == test_scope
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
        test_scope: str,
    ):
        """Test adding a team member with minimal required fields."""
        member_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/teams/{team.id}/members", json=member_data)

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["scope"] == test_scope
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_team_member_duplicate(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test that adding a duplicate team member fails."""
        # Add member directly in database
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

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
        non_existent_team_id = uuid4()
        member_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/teams/{non_existent_team_id}/members", json=member_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_team_member_wrong_scope(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        principal: KPrincipal,
        test_user_id: UUID,
    ):
        """Test that adding a member to a team in different scope fails."""
        # Create team in different scope
        other_team = KTeam(
            name="Other Team",
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_team)
        await async_session.commit()
        await async_session.refresh(other_team)

        member_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/teams/{other_team.id}/members", json=member_data
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
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test listing team members with a single member."""
        # Add a member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        test_scope: str,
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
                scope=test_scope,
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
        non_existent_team_id = uuid4()

        response = await client.get(f"/teams/{non_existent_team_id}/members")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_team_members_scope_isolation(
        self,
        client: AsyncClient,
        team: KTeam,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test that listing members respects scope isolation."""
        # Create principal and add as member in correct scope
        principal1 = KPrincipal(
            username="user1",
            primary_email="user1@example.com",
            first_name="User",
            last_name="One",
            display_name="User One",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(principal1)
        await async_session.commit()
        await async_session.refresh(principal1)

        member_in_scope = KTeamMember(
            team_id=team.id,
            principal_id=principal1.id,
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member_in_scope)

        # Create another principal and add as member in different scope
        principal2 = KPrincipal(
            username="user2",
            primary_email="user2@example.com",
            first_name="User",
            last_name="Two",
            display_name="User Two",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(principal2)
        await async_session.commit()
        await async_session.refresh(principal2)

        member_out_scope = KTeamMember(
            team_id=team.id,
            principal_id=principal2.id,
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member_out_scope)
        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/members")

        assert response.status_code == 200
        data = response.json()
        assert len(data["members"]) == 1
        assert data["members"][0]["principal_id"] == str(principal1.id)


class TestGetTeamMember:
    """Test suite for GET /teams/{team_id}/members/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_team_member_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test successfully getting a single team member."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        non_existent_principal_id = uuid4()

        response = await client.get(
            f"/teams/{team.id}/members/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_team_member_wrong_scope(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that getting a member in different scope returns 404."""
        # Add member in different scope
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/members/{principal.id}")

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
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating a team member's role."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating a team member's metadata."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating both role and meta."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        non_existent_principal_id = uuid4()
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
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test successfully removing a team member."""
        # Add member
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope=test_scope,
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
        non_existent_principal_id = uuid4()

        response = await client.delete(
            f"/teams/{team.id}/members/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_team_member_wrong_scope(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that removing a member in different scope returns 404."""
        # Add member in different scope
        member = KTeamMember(
            team_id=team.id,
            principal_id=principal.id,
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(member)
        await async_session.commit()

        response = await client.delete(f"/teams/{team.id}/members/{principal.id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

        # Verify member still exists
        from sqlmodel import select

        result = await async_session.execute(
            select(KTeamMember).where(
                KTeamMember.team_id == team.id,
                KTeamMember.principal_id == principal.id,
            )
        )
        assert result.scalar_one_or_none() is not None
