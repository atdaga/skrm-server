"""Unit tests for sprint team management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KSprint, KSprintTeam, KTeam
from app.routes.v1.sprint_teams import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with sprint_teams router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


@pytest.fixture
async def sprint(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KSprint:
    """Create a test sprint."""
    sprint = KSprint(
        title="Test Sprint",
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(sprint)
    await async_session.commit()
    await async_session.refresh(sprint)
    return sprint


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


class TestAddSprintTeam:
    """Test suite for POST /sprints/{sprint_id}/teams endpoint."""

    async def test_add_sprint_team_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new team to a sprint."""
        team_data = {
            "team_id": str(team.id),
            "role": "development",
            "meta": {
                "capacity": 10,
                "focus_areas": ["backend", "testing"],
            },
        }

        response = await client.post(f"/sprints/{sprint.id}/teams", json=team_data)

        assert response.status_code == 201
        data = response.json()
        assert data["sprint_id"] == str(sprint.id)
        assert data["team_id"] == str(team.id)
        assert data["role"] == "development"
        assert data["meta"] == {
            "capacity": 10,
            "focus_areas": ["backend", "testing"],
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_add_sprint_team_minimal_fields(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
    ):
        """Test adding a team with only required fields."""
        team_data = {"team_id": str(team.id)}

        response = await client.post(f"/sprints/{sprint.id}/teams", json=team_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    async def test_add_sprint_team_duplicate(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
    ):
        """Test that adding the same team twice fails."""
        team_data = {"team_id": str(team.id), "role": "development"}

        # Add team first time
        response = await client.post(f"/sprints/{sprint.id}/teams", json=team_data)
        assert response.status_code == 201

        # Try to add the same team again
        response = await client.post(f"/sprints/{sprint.id}/teams", json=team_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_add_sprint_team_nonexistent_sprint(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test that adding a team to a non-existent sprint fails."""
        non_existent_sprint_id = uuid7()
        team_data = {"team_id": str(team.id)}

        response = await client.post(
            f"/sprints/{non_existent_sprint_id}/teams", json=team_data
        )
        assert response.status_code == 404

    async def test_add_sprint_team_nonexistent_team(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test that adding a non-existent team fails."""
        non_existent_team_id = uuid7()
        team_data = {"team_id": str(non_existent_team_id)}

        response = await client.post(f"/sprints/{sprint.id}/teams", json=team_data)
        assert response.status_code == 404


class TestListSprintTeams:
    """Test suite for GET /sprints/{sprint_id}/teams endpoint."""

    async def test_list_sprint_teams_empty(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test listing teams when none exist."""
        response = await client.get(f"/sprints/{sprint.id}/teams")

        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []

    async def test_list_sprint_teams_multiple(
        self,
        client: AsyncClient,
        sprint: KSprint,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple teams."""
        # Create multiple teams
        team1 = KTeam(
            name="Frontend Team",
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        team2 = KTeam(
            name="Backend Team",
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([team1, team2])
        await async_session.commit()
        await async_session.refresh(team1)
        await async_session.refresh(team2)

        # Add both teams to the sprint
        sprint_team1 = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team1.id,
            org_id=test_org_id,
            role="frontend",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        sprint_team2 = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team2.id,
            org_id=test_org_id,
            role="backend",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([sprint_team1, sprint_team2])
        await async_session.commit()

        response = await client.get(f"/sprints/{sprint.id}/teams")

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 2
        team_roles = [t["role"] for t in data["teams"]]
        assert "frontend" in team_roles
        assert "backend" in team_roles

    async def test_list_sprint_teams_nonexistent_sprint(
        self,
        client: AsyncClient,
    ):
        """Test listing teams for a non-existent sprint."""
        non_existent_id = uuid7()

        response = await client.get(f"/sprints/{non_existent_id}/teams")
        assert response.status_code == 404


class TestGetSprintTeam:
    """Test suite for GET /sprints/{sprint_id}/teams/{team_id} endpoint."""

    async def test_get_sprint_team_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a sprint team."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="qa",
            meta={"test_coverage": "90%"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_team)
        await async_session.commit()
        await async_session.refresh(sprint_team)

        response = await client.get(f"/sprints/{sprint.id}/teams/{team.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["sprint_id"] == str(sprint.id)
        assert data["team_id"] == str(team.id)
        assert data["role"] == "qa"
        assert data["meta"] == {"test_coverage": "90%"}

    async def test_get_sprint_team_not_found(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test getting a non-existent sprint team."""
        non_existent_team_id = uuid7()

        response = await client.get(
            f"/sprints/{sprint.id}/teams/{non_existent_team_id}"
        )
        assert response.status_code == 404


class TestUpdateSprintTeam:
    """Test suite for PATCH /sprints/{sprint_id}/teams/{team_id} endpoint."""

    async def test_update_sprint_team_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a sprint team."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_team)
        await async_session.commit()
        await async_session.refresh(sprint_team)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/sprints/{sprint.id}/teams/{team.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    async def test_update_sprint_team_partial(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a sprint team."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_team)
        await async_session.commit()
        await async_session.refresh(sprint_team)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/sprints/{sprint.id}/teams/{team.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    async def test_update_sprint_team_not_found(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test updating a non-existent sprint team."""
        non_existent_team_id = uuid7()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/sprints/{sprint.id}/teams/{non_existent_team_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveSprintTeam:
    """Test suite for DELETE /sprints/{sprint_id}/teams/{team_id} endpoint."""

    async def test_remove_sprint_team_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a team from a sprint."""
        sprint_team = KSprintTeam(
            sprint_id=sprint.id,
            team_id=team.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_team)
        await async_session.commit()
        await async_session.refresh(sprint_team)

        response = await client.delete(f"/sprints/{sprint.id}/teams/{team.id}")

        assert response.status_code == 204

        # Verify sprint team is deleted
        get_response = await client.get(f"/sprints/{sprint.id}/teams/{team.id}")
        assert get_response.status_code == 404

    async def test_remove_sprint_team_not_found(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test removing a non-existent sprint team."""
        non_existent_team_id = uuid7()

        response = await client.delete(
            f"/sprints/{sprint.id}/teams/{non_existent_team_id}"
        )
        assert response.status_code == 404
