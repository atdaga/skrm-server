"""Unit tests for project team management endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KProject, KProjectTeam, KTeam
from app.routes.v1.project_teams import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with project_teams router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


@pytest.fixture
async def project(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KProject:
    """Create a test project."""
    project = KProject(
        name="Test Project",
        description="A test project",
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)
    return project


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


class TestAddProjectTeam:
    """Test suite for POST /projects/{project_id}/teams endpoint."""

    @pytest.mark.asyncio
    async def test_add_project_team_success(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new team to a project."""
        team_data = {
            "team_id": str(team.id),
            "role": "development",
            "meta": {
                "access_level": "full",
                "responsibilities": ["backend", "testing"],
            },
        }

        response = await client.post(f"/projects/{project.id}/teams", json=team_data)

        assert response.status_code == 201
        data = response.json()
        assert data["project_id"] == str(project.id)
        assert data["team_id"] == str(team.id)
        assert data["role"] == "development"
        assert data["meta"] == {
            "access_level": "full",
            "responsibilities": ["backend", "testing"],
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_add_project_team_minimal_fields(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
    ):
        """Test adding a team with only required fields."""
        team_data = {"team_id": str(team.id)}

        response = await client.post(f"/projects/{project.id}/teams", json=team_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_project_team_duplicate(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
    ):
        """Test that adding the same team twice fails."""
        team_data = {"team_id": str(team.id), "role": "development"}

        # Add team first time
        response = await client.post(f"/projects/{project.id}/teams", json=team_data)
        assert response.status_code == 201

        # Try to add the same team again
        response = await client.post(f"/projects/{project.id}/teams", json=team_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_project_team_nonexistent_project(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test that adding a team to a non-existent project fails."""
        non_existent_project_id = uuid4()
        team_data = {"team_id": str(team.id)}

        response = await client.post(
            f"/projects/{non_existent_project_id}/teams", json=team_data
        )
        assert response.status_code == 404


class TestListProjectTeams:
    """Test suite for GET /projects/{project_id}/teams endpoint."""

    @pytest.mark.asyncio
    async def test_list_project_teams_empty(
        self,
        client: AsyncClient,
        project: KProject,
    ):
        """Test listing teams when none exist."""
        response = await client.get(f"/projects/{project.id}/teams")

        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []

    @pytest.mark.asyncio
    async def test_list_project_teams_multiple(
        self,
        client: AsyncClient,
        project: KProject,
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

        # Add both teams to the project
        project_team1 = KProjectTeam(
            project_id=project.id,
            team_id=team1.id,
            org_id=test_org_id,
            role="frontend",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        project_team2 = KProjectTeam(
            project_id=project.id,
            team_id=team2.id,
            org_id=test_org_id,
            role="backend",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([project_team1, project_team2])
        await async_session.commit()

        response = await client.get(f"/projects/{project.id}/teams")

        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 2
        team_roles = [t["role"] for t in data["teams"]]
        assert "frontend" in team_roles
        assert "backend" in team_roles

    @pytest.mark.asyncio
    async def test_list_project_teams_nonexistent_project(
        self,
        client: AsyncClient,
    ):
        """Test listing teams for a non-existent project."""
        non_existent_id = uuid4()

        response = await client.get(f"/projects/{non_existent_id}/teams")
        assert response.status_code == 404


class TestGetProjectTeam:
    """Test suite for GET /projects/{project_id}/teams/{team_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_project_team_success(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a project team."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="qa",
            meta={"test_coverage": "90%"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project_team)
        await async_session.commit()
        await async_session.refresh(project_team)

        response = await client.get(f"/projects/{project.id}/teams/{team.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == str(project.id)
        assert data["team_id"] == str(team.id)
        assert data["role"] == "qa"
        assert data["meta"] == {"test_coverage": "90%"}

    @pytest.mark.asyncio
    async def test_get_project_team_not_found(
        self,
        client: AsyncClient,
        project: KProject,
    ):
        """Test getting a non-existent project team."""
        non_existent_team_id = uuid4()

        response = await client.get(
            f"/projects/{project.id}/teams/{non_existent_team_id}"
        )
        assert response.status_code == 404


class TestUpdateProjectTeam:
    """Test suite for PATCH /projects/{project_id}/teams/{team_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_project_team_success(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a project team."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project_team)
        await async_session.commit()
        await async_session.refresh(project_team)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/projects/{project.id}/teams/{team.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    @pytest.mark.asyncio
    async def test_update_project_team_partial(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a project team."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project_team)
        await async_session.commit()
        await async_session.refresh(project_team)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/projects/{project.id}/teams/{team.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    @pytest.mark.asyncio
    async def test_update_project_team_not_found(
        self,
        client: AsyncClient,
        project: KProject,
    ):
        """Test updating a non-existent project team."""
        non_existent_team_id = uuid4()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/projects/{project.id}/teams/{non_existent_team_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveProjectTeam:
    """Test suite for DELETE /projects/{project_id}/teams/{team_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_project_team_success(
        self,
        client: AsyncClient,
        project: KProject,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a team from a project."""
        project_team = KProjectTeam(
            project_id=project.id,
            team_id=team.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project_team)
        await async_session.commit()
        await async_session.refresh(project_team)

        response = await client.delete(f"/projects/{project.id}/teams/{team.id}")

        assert response.status_code == 204

        # Verify project team is deleted
        get_response = await client.get(f"/projects/{project.id}/teams/{team.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_project_team_not_found(
        self,
        client: AsyncClient,
        project: KProject,
    ):
        """Test removing a non-existent project team."""
        non_existent_team_id = uuid4()

        response = await client.delete(
            f"/projects/{project.id}/teams/{non_existent_team_id}"
        )
        assert response.status_code == 404
