"""Unit tests for team management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KTeam
from app.routes.deps import get_current_token
from app.routes.v1.teams import router
from app.schemas.user import TokenData


@pytest.fixture
def app_with_overrides(async_session: AsyncSession, mock_token_data: TokenData) -> FastAPI:
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
        transport=ASGITransport(app=app_with_overrides),
        base_url="http://test"
    ) as ac:
        yield ac


class TestCreateTeam:
    """Test suite for POST /teams endpoint."""

    @pytest.mark.asyncio
    async def test_create_team_success(
        self,
        client: AsyncClient,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test successfully creating a new team."""
        team_data = {
            "name": "Engineering Team",
            "meta": {"department": "Engineering", "location": "SF"}
        }
        
        response = await client.post("/teams", json=team_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering Team"
        assert data["scope"] == test_scope
        assert data["meta"] == {"department": "Engineering", "location": "SF"}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_create_team_minimal_data(
        self,
        client: AsyncClient,
        test_scope: str,
    ):
        """Test creating a team with minimal required fields."""
        team_data = {
            "name": "Minimal Team"
        }
        
        response = await client.post("/teams", json=team_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Team"
        assert data["scope"] == test_scope
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_team_duplicate_name_in_scope(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test that creating a team with duplicate name in same scope fails."""
        # Create first team directly in database
        team = KTeam(
            name="Duplicate Team",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        
        # Try to create another team with same name
        team_data = {
            "name": "Duplicate Team",
            "meta": {}
        }
        
        response = await client.post("/teams", json=team_data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_team_with_empty_meta(
        self,
        client: AsyncClient,
    ):
        """Test creating a team with explicitly empty meta."""
        team_data = {
            "name": "Empty Meta Team",
            "meta": {}
        }
        
        response = await client.post("/teams", json=team_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_team_with_complex_meta(
        self,
        client: AsyncClient,
    ):
        """Test creating a team with complex nested metadata."""
        team_data = {
            "name": "Complex Meta Team",
            "meta": {
                "department": "Engineering",
                "settings": {
                    "notifications": True,
                    "visibility": "private"
                },
                "tags": ["backend", "api", "microservices"],
                "member_count": 10
            }
        }
        
        response = await client.post("/teams", json=team_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == team_data["meta"]


class TestListTeams:
    """Test suite for GET /teams endpoint."""

    @pytest.mark.asyncio
    async def test_list_teams_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing teams when none exist."""
        response = await client.get("/teams")
        
        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []

    @pytest.mark.asyncio
    async def test_list_teams_single(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test listing teams with a single team."""
        # Create a team
        team = KTeam(
            name="Test Team",
            scope=test_scope,
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        response = await client.get("/teams")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["teams"][0]["name"] == "Test Team"
        assert data["teams"][0]["id"] == str(team.id)

    @pytest.mark.asyncio
    async def test_list_teams_multiple(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test listing multiple teams."""
        # Create multiple teams
        teams_data = [
            {"name": "Team Alpha", "meta": {"priority": 1}},
            {"name": "Team Beta", "meta": {"priority": 2}},
            {"name": "Team Gamma", "meta": {"priority": 3}},
        ]
        
        for team_data in teams_data:
            team = KTeam(
                name=team_data["name"],
                scope=test_scope,
                meta=team_data["meta"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(team)
        
        await async_session.commit()
        
        response = await client.get("/teams")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 3
        team_names = {team["name"] for team in data["teams"]}
        assert team_names == {"Team Alpha", "Team Beta", "Team Gamma"}

    @pytest.mark.asyncio
    async def test_list_teams_scope_isolation(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test that listing teams only returns teams in the user's scope."""
        # Create team in user's scope
        team_in_scope = KTeam(
            name="Team In Scope",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team_in_scope)
        
        # Create team in different scope
        team_out_scope = KTeam(
            name="Team Out Of Scope",
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team_out_scope)
        
        await async_session.commit()
        
        response = await client.get("/teams")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["teams"][0]["name"] == "Team In Scope"


class TestGetTeam:
    """Test suite for GET /teams/{team_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_team_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test successfully getting a single team by ID."""
        # Create a team
        team = KTeam(
            name="Test Team",
            scope=test_scope,
            meta={"department": "Engineering"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        response = await client.get(f"/teams/{team.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team.id)
        assert data["name"] == "Test Team"
        assert data["scope"] == test_scope
        assert data["meta"] == {"department": "Engineering"}

    @pytest.mark.asyncio
    async def test_get_team_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting a team that doesn't exist."""
        non_existent_id = uuid4()
        
        response = await client.get(f"/teams/{non_existent_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_team_wrong_scope(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that getting a team in a different scope returns 404."""
        # Create team in different scope
        team = KTeam(
            name="Other Scope Team",
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        response = await client.get(f"/teams/{team.id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_team_invalid_uuid(
        self,
        client: AsyncClient,
    ):
        """Test getting a team with an invalid UUID."""
        response = await client.get("/teams/not-a-uuid")
        
        assert response.status_code == 422  # Validation error


class TestUpdateTeam:
    """Test suite for PATCH /teams/{team_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_team_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating a team's name."""
        # Create a team
        team = KTeam(
            name="Old Name",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        update_data = {
            "name": "New Name"
        }
        
        response = await client.patch(f"/teams/{team.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["id"] == str(team.id)

    @pytest.mark.asyncio
    async def test_update_team_meta(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating a team's metadata."""
        # Create a team
        team = KTeam(
            name="Test Team",
            scope=test_scope,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        update_data = {
            "meta": {"new": "data", "updated": True}
        }
        
        response = await client.patch(f"/teams/{team.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}
        assert data["name"] == "Test Team"  # Name unchanged

    @pytest.mark.asyncio
    async def test_update_team_both_fields(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating both name and meta."""
        # Create a team
        team = KTeam(
            name="Old Name",
            scope=test_scope,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        update_data = {
            "name": "New Name",
            "meta": {"new": "data"}
        }
        
        response = await client.patch(f"/teams/{team.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["meta"] == {"new": "data"}

    @pytest.mark.asyncio
    async def test_update_team_not_found(
        self,
        client: AsyncClient,
    ):
        """Test updating a team that doesn't exist."""
        non_existent_id = uuid4()
        update_data = {
            "name": "New Name"
        }
        
        response = await client.patch(f"/teams/{non_existent_id}", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_team_wrong_scope(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a team in a different scope returns 404."""
        # Create team in different scope
        team = KTeam(
            name="Other Scope Team",
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        update_data = {
            "name": "New Name"
        }
        
        response = await client.patch(f"/teams/{team.id}", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_team_duplicate_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test that updating to a duplicate name fails."""
        # Create two teams
        team1 = KTeam(
            name="Team One",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        team2 = KTeam(
            name="Team Two",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team1)
        async_session.add(team2)
        await async_session.commit()
        await async_session.refresh(team2)
        
        # Try to rename team2 to team1's name
        update_data = {
            "name": "Team One"
        }
        
        response = await client.patch(f"/teams/{team2.id}", json=update_data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_team_empty_payload(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Create a team
        team = KTeam(
            name="Test Team",
            scope=test_scope,
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        update_data = {}
        
        response = await client.patch(f"/teams/{team.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Team"  # Unchanged
        assert data["meta"] == {"key": "value"}  # Unchanged

    @pytest.mark.asyncio
    async def test_update_team_audit_fields(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test that audit fields are updated correctly."""
        # Create a team
        team = KTeam(
            name="Test Team",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        original_modified = team.last_modified
        
        update_data = {
            "name": "Updated Team"
        }
        
        response = await client.patch(f"/teams/{team.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["last_modified_by"] == str(test_user_id)
        # Note: We can't easily test that last_modified changed in this test
        # as it depends on timing, but the field should be present


class TestDeleteTeam:
    """Test suite for DELETE /teams/{team_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_team_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_scope: str,
        test_user_id: UUID,
    ):
        """Test successfully deleting a team."""
        # Create a team
        team = KTeam(
            name="Team To Delete",
            scope=test_scope,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        team_id = team.id
        
        response = await client.delete(f"/teams/{team_id}")
        
        assert response.status_code == 204
        assert response.content == b""  # No content in response
        
        # Verify team is actually deleted
        result = await async_session.get(KTeam, team_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_team_not_found(
        self,
        client: AsyncClient,
    ):
        """Test deleting a team that doesn't exist."""
        non_existent_id = uuid4()
        
        response = await client.delete(f"/teams/{non_existent_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_team_wrong_scope(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a team in a different scope returns 404."""
        # Create team in different scope
        team = KTeam(
            name="Other Scope Team",
            scope="other-tenant",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        
        response = await client.delete(f"/teams/{team.id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        
        # Verify team still exists
        result = await async_session.get(KTeam, team.id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_delete_team_invalid_uuid(
        self,
        client: AsyncClient,
    ):
        """Test deleting a team with an invalid UUID."""
        response = await client.delete("/teams/not-a-uuid")
        
        assert response.status_code == 422  # Validation error

