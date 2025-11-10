"""Unit tests for team management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KTeam
from app.routes.v1.teams import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with teams router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestCreateTeam:
    """Test suite for POST /teams endpoint."""

    async def test_create_team_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
        test_scope: str,
    ):
        """Test successfully creating a new team."""
        team_data = {
            "name": "Engineering Team",
            "meta": {"department": "Engineering", "location": "SF"},
        }

        response = await client.post(
            f"/teams?org_id={test_organization.id}", json=team_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering Team"
        assert data["meta"] == {"department": "Engineering", "location": "SF"}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_create_team_minimal_data(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_scope: str,
    ):
        """Test creating a team with minimal required fields."""
        team_data = {"name": "Minimal Team"}

        response = await client.post(
            f"/teams?org_id={test_organization.id}", json=team_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Team"
        assert data["meta"] == {}

    async def test_create_team_duplicate_name_in_scope(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test that creating a team with duplicate name in same scope fails."""
        # Create first team directly in database
        team = KTeam(
            name="Duplicate Team",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()

        # Try to create another team with same name
        team_data = {"name": "Duplicate Team", "meta": {}}

        response = await client.post(
            f"/teams?org_id={test_organization.id}", json=team_data
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_create_team_with_empty_meta(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test creating a team with explicitly empty meta."""
        team_data = {"name": "Empty Meta Team", "meta": {}}

        response = await client.post(
            f"/teams?org_id={test_organization.id}", json=team_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == {}

    async def test_create_team_with_complex_meta(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test creating a team with complex nested metadata."""
        team_data = {
            "name": "Complex Meta Team",
            "meta": {
                "department": "Engineering",
                "settings": {"notifications": True, "visibility": "private"},
                "tags": ["backend", "api", "microservices"],
                "member_count": 10,
            },
        }

        response = await client.post(
            f"/teams?org_id={test_organization.id}", json=team_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == team_data["meta"]


class TestListTeams:
    """Test suite for GET /teams endpoint."""

    async def test_list_teams_empty(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test listing teams when none exist."""
        response = await client.get(f"/teams?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []

    async def test_list_teams_single(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test listing teams with a single team."""
        # Create a team
        team = KTeam(
            name="Test Team",
            org_id=test_organization.id,
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        response = await client.get(f"/teams?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["teams"][0]["name"] == "Test Team"
        assert data["teams"][0]["id"] == str(team.id)

    async def test_list_teams_multiple(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
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
                org_id=test_organization.id,
                meta=team_data["meta"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(team)

        await async_session.commit()

        response = await client.get(f"/teams?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 3
        team_names = {team["name"] for team in data["teams"]}
        assert team_names == {"Team Alpha", "Team Beta", "Team Gamma"}


class TestGetTeam:
    """Test suite for GET /teams/{team_id} endpoint."""

    async def test_get_team_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
        test_scope: str,
    ):
        """Test successfully getting a single team by ID."""
        # Create a team
        team = KTeam(
            name="Test Team",
            org_id=test_organization.id,
            meta={"department": "Engineering"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        response = await client.get(f"/teams/{team.id}?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team.id)
        assert data["name"] == "Test Team"
        assert data["meta"] == {"department": "Engineering"}

    async def test_get_team_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test getting a team that doesn't exist."""
        non_existent_id = uuid7()

        response = await client.get(
            f"/teams/{non_existent_id}?org_id={test_organization.id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_get_team_invalid_uuid(
        self,
        client: AsyncClient,
    ):
        """Test getting a team with an invalid UUID."""
        response = await client.get("/teams/not-a-uuid")

        assert response.status_code == 422  # Validation error


class TestUpdateTeam:
    """Test suite for PATCH /teams/{team_id} endpoint."""

    async def test_update_team_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test updating a team's name."""
        # Create a team
        team = KTeam(
            name="Old Name",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        update_data = {"name": "New Name"}

        response = await client.patch(
            f"/teams/{team.id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["id"] == str(team.id)

    async def test_update_team_meta(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test updating a team's metadata."""
        # Create a team
        team = KTeam(
            name="Test Team",
            org_id=test_organization.id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        update_data = {"meta": {"new": "data", "updated": True}}

        response = await client.patch(
            f"/teams/{team.id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}
        assert data["name"] == "Test Team"  # Name unchanged

    async def test_update_team_both_fields(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test updating both name and meta."""
        # Create a team
        team = KTeam(
            name="Old Name",
            org_id=test_organization.id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        update_data = {"name": "New Name", "meta": {"new": "data"}}

        response = await client.patch(
            f"/teams/{team.id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["meta"] == {"new": "data"}

    async def test_update_team_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test updating a team that doesn't exist."""
        non_existent_id = uuid7()
        update_data = {"name": "New Name"}

        response = await client.patch(
            f"/teams/{non_existent_id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_update_team_duplicate_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test that updating to a duplicate name fails."""
        # Create two teams
        team1 = KTeam(
            name="Team One",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        team2 = KTeam(
            name="Team Two",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team1)
        async_session.add(team2)
        await async_session.commit()
        await async_session.refresh(team2)

        # Try to rename team2 to team1's name
        update_data = {"name": "Team One"}

        response = await client.patch(
            f"/teams/{team2.id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_update_team_empty_payload(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Create a team
        team = KTeam(
            name="Test Team",
            org_id=test_organization.id,
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        update_data = {}

        response = await client.patch(
            f"/teams/{team.id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Team"  # Unchanged
        assert data["meta"] == {"key": "value"}  # Unchanged

    async def test_update_team_audit_fields(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test that audit fields are updated correctly."""
        # Create a team
        team = KTeam(
            name="Test Team",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        update_data = {"name": "Updated Team"}

        response = await client.patch(
            f"/teams/{team.id}?org_id={test_organization.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["last_modified_by"] == str(test_user_id)
        # Note: We can't easily test that last_modified changed in this test
        # as it depends on timing, but the field should be present


class TestDeleteTeam:
    """Test suite for DELETE /teams/{team_id} endpoint."""

    async def test_delete_team_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test successfully deleting a team."""
        # Create a team
        team = KTeam(
            name="Team To Delete",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)
        team_id = team.id

        response = await client.delete(
            f"/teams/{team_id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204
        assert response.content == b""  # No content in response

        # Verify team is soft-deleted
        await async_session.refresh(team)
        assert team.deleted_at is not None

    async def test_delete_team_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test deleting a team that doesn't exist."""
        non_existent_id = uuid7()

        response = await client.delete(
            f"/teams/{non_existent_id}?org_id={test_organization.id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_delete_team_invalid_uuid(
        self,
        client: AsyncClient,
    ):
        """Test deleting a team with an invalid UUID."""
        response = await client.delete("/teams/not-a-uuid")

        assert response.status_code == 422  # Validation error


class TestUnauthorizedAccess:
    """Test suite for unauthorized access scenarios."""

    async def test_create_team_unauthorized(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test creating a team in an organization user is not a member of."""
        # Create an organization WITHOUT adding test user as member
        org = KOrganization(
            name="Unauthorized Org",
            alias="unauth_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        team_data = {"name": "Unauthorized Team"}
        response = await client.post(f"/teams?org_id={org.id}", json=team_data)

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    async def test_list_teams_unauthorized(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing teams in an organization user is not a member of."""
        # Create an organization WITHOUT adding test user as member
        org = KOrganization(
            name="Unauthorized Org",
            alias="unauth_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        response = await client.get(f"/teams?org_id={org.id}")

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    async def test_get_team_unauthorized(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a team in an organization user is not a member of."""
        # Create an organization WITHOUT adding test user as member
        org = KOrganization(
            name="Unauthorized Org",
            alias="unauth_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Create a team in that org
        team = KTeam(
            name="Team",
            org_id=org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        response = await client.get(f"/teams/{team.id}?org_id={org.id}")

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    async def test_update_team_unauthorized(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating a team in an organization user is not a member of."""
        # Create an organization WITHOUT adding test user as member
        org = KOrganization(
            name="Unauthorized Org",
            alias="unauth_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Create a team in that org
        team = KTeam(
            name="Team",
            org_id=org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        update_data = {"name": "Updated Name"}
        response = await client.patch(
            f"/teams/{team.id}?org_id={org.id}", json=update_data
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    async def test_delete_team_unauthorized(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test deleting a team in an organization user is not a member of."""
        # Create an organization WITHOUT adding test user as member
        org = KOrganization(
            name="Unauthorized Org",
            alias="unauth_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Create a team in that org
        team = KTeam(
            name="Team",
            org_id=org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        response = await client.delete(f"/teams/{team.id}?org_id={org.id}")

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()
