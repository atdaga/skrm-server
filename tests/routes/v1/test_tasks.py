"""Unit tests for task management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KTask, KTeam
from app.models.k_task import TaskStatus
from app.routes.v1.tasks import router
from tests.conftest import get_test_org_id, get_test_task_id


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with tasks router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


@pytest.fixture
async def test_team(
    async_session: AsyncSession,
    test_organization: KOrganization,
    test_user_id: UUID,
):
    """Create a test team for task testing."""
    team = KTeam(
        name="Test Team",
        org_id=test_organization.id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(team)
    await async_session.commit()
    await async_session.refresh(team)
    return team


class TestCreateTask:
    """Test suite for POST /tasks endpoint."""

    async def test_create_task_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        test_user_id: UUID,
    ):
        """Test successfully creating a new task."""
        task_data = {
            "summary": "Build user authentication system",
            "description": "Implement OAuth 2.0 based authentication",
            "team_id": str(test_team.id),
            "guestimate": 8.0,
            "status": "InProgress",
            "meta": {"priority": "high"},
        }

        response = await client.post(
            f"/tasks?org_id={test_organization.id}", json=task_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["summary"] == "Build user authentication system"
        assert data["description"] == "Implement OAuth 2.0 based authentication"
        assert data["team_id"] == str(test_team.id)
        assert data["guestimate"] == 8.0
        assert data["status"] == "InProgress"
        assert data["review_result"] is None
        assert data["meta"] == {"priority": "high"}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_create_task_minimal_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
    ):
        """Test creating a task with only required fields."""
        task_data = {
            "team_id": str(test_team.id),
        }

        response = await client.post(
            f"/tasks?org_id={test_organization.id}", json=task_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == str(test_team.id)
        assert data["summary"] is None
        assert data["description"] is None
        assert data["guestimate"] is None
        assert data["status"] == "Backlog"  # Default status
        assert data["review_result"] is None
        assert data["meta"] == {}

    async def test_create_task_with_review_result(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
    ):
        """Test creating a task with a review result."""
        task_data = {
            "team_id": str(test_team.id),
            "status": "Review",
            "review_result": "Passed",
        }

        response = await client.post(
            f"/tasks?org_id={test_organization.id}", json=task_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "Review"
        assert data["review_result"] == "Passed"

    async def test_create_task_unauthorized_org(
        self, client: AsyncClient, test_team: KTeam
    ):
        """Test that creating a task in unauthorized org fails."""
        unauthorized_org_id = uuid7()
        task_data = {
            "team_id": str(test_team.id),
        }

        response = await client.post(
            f"/tasks?org_id={unauthorized_org_id}", json=task_data
        )
        assert response.status_code == 403

    async def test_create_task_increments_id_from_existing(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that creating a task increments ID based on existing tasks."""
        # Create an existing task directly in the database
        existing_task = KTask(
            id=get_test_task_id(test_organization.id),
            summary="Existing task",
            org_id=test_organization.id,
            team_id=test_team.id,
            status=TaskStatus.BACKLOG,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(existing_task)
        await async_session.commit()

        # Now create a new task via the API (which uses get_next_task_number)
        task_data = {
            "team_id": str(test_team.id),
            "summary": "New task after existing",
        }

        response = await client.post(
            f"/tasks?org_id={test_organization.id}", json=task_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["summary"] == "New task after existing"
        # The new task should have a higher task number than the existing one
        new_task_id = UUID(data["id"])
        existing_task_number = int(str(existing_task.id).split("-")[4])
        new_task_number = int(str(new_task_id).split("-")[4])
        assert new_task_number > existing_task_number


class TestListTasks:
    """Test suite for GET /tasks endpoint."""

    async def test_list_tasks_empty(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test listing tasks when none exist."""
        response = await client.get(f"/tasks?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []

    async def test_list_tasks_multiple(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple tasks."""
        # Create multiple tasks
        tasks = [
            KTask(
                id=get_test_task_id(test_organization.id),
                summary="First task summary",
                org_id=test_organization.id,
                team_id=test_team.id,
                status=TaskStatus.BACKLOG,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
            KTask(
                id=get_test_task_id(test_organization.id),
                summary="Second task summary",
                org_id=test_organization.id,
                team_id=test_team.id,
                status=TaskStatus.IN_PROGRESS,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
        ]

        for task in tasks:
            async_session.add(task)
        await async_session.commit()

        response = await client.get(f"/tasks?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        task_summaries = [t["summary"] for t in data["tasks"]]
        assert "First task summary" in task_summaries
        assert "Second task summary" in task_summaries

    async def test_list_tasks_unauthorized_org(self, client: AsyncClient):
        """Test that listing tasks in unauthorized org fails."""
        unauthorized_org_id = uuid7()

        response = await client.get(f"/tasks?org_id={unauthorized_org_id}")
        assert response.status_code == 403


class TestGetTask:
    """Test suite for GET /tasks/{task_id} endpoint."""

    async def test_get_task_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a task."""
        task = KTask(
            id=get_test_task_id(test_organization.id),
            summary="Test summary",
            org_id=test_organization.id,
            team_id=test_team.id,
            status=TaskStatus.IN_PROGRESS,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        response = await client.get(f"/tasks/{task.id}?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(task.id)
        assert data["summary"] == "Test summary"
        assert data["status"] == "InProgress"

    async def test_get_task_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test getting a non-existent task."""
        non_existent_id = uuid7()

        response = await client.get(
            f"/tasks/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    async def test_get_task_wrong_org(
        self,
        client: AsyncClient,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a task with wrong org_id."""
        other_org = KOrganization(
            id=get_test_org_id(),
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        task = KTask(
            id=get_test_task_id(other_org.id),
            summary="Secret task summary",
            org_id=other_org.id,
            team_id=test_team.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        # Try to access with unauthorized org
        wrong_org_id = uuid7()
        response = await client.get(f"/tasks/{task.id}?org_id={wrong_org_id}")
        assert response.status_code == 403


class TestUpdateTask:
    """Test suite for PATCH /tasks/{task_id} endpoint."""

    async def test_update_task_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully updating a task."""
        task = KTask(
            id=get_test_task_id(test_organization.id),
            summary="Old summary",
            org_id=test_organization.id,
            team_id=test_team.id,
            status=TaskStatus.BACKLOG,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        update_data = {
            "summary": "Updated summary",
            "status": "InProgress",
            "review_result": "Passed",
            "meta": {"priority": "medium"},
        }

        response = await client.patch(
            f"/tasks/{task.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Updated summary"
        assert data["status"] == "InProgress"
        assert data["review_result"] == "Passed"
        assert data["meta"] == {"priority": "medium"}

    async def test_update_task_partial(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a task."""
        task = KTask(
            id=get_test_task_id(test_organization.id),
            summary="Original summary",
            guestimate=3.0,
            org_id=test_organization.id,
            team_id=test_team.id,
            status=TaskStatus.BACKLOG,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        update_data = {"guestimate": 5.0, "status": "InProgress"}

        response = await client.patch(
            f"/tasks/{task.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Original summary"  # Unchanged
        assert data["guestimate"] == 5.0  # Changed
        assert data["status"] == "InProgress"  # Changed

    async def test_update_task_all_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating all fields of a task."""
        # Create two teams
        team1 = KTeam(
            name="Team 1",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        team2 = KTeam(
            name="Team 2",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([team1, team2])
        await async_session.commit()
        await async_session.refresh(team1)
        await async_session.refresh(team2)

        # Create a task with initial values
        task = KTask(
            id=get_test_task_id(test_organization.id),
            summary="Initial summary",
            description="Initial description",
            team_id=team1.id,
            guestimate=3.0,
            status=TaskStatus.BACKLOG,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        # Update all fields
        update_data = {
            "summary": "Updated summary",
            "description": "Updated description with more details",
            "team_id": str(team2.id),
            "guestimate": 7.5,
            "status": "Done",
            "review_result": "Passed",
            "meta": {"updated": True},
        }

        response = await client.patch(
            f"/tasks/{task.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Updated summary"
        assert data["description"] == "Updated description with more details"
        assert data["team_id"] == str(team2.id)
        assert data["guestimate"] == 7.5
        assert data["status"] == "Done"
        assert data["review_result"] == "Passed"
        assert data["meta"] == {"updated": True}

    async def test_update_task_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test updating a non-existent task."""
        non_existent_id = uuid7()
        update_data = {"summary": "New summary"}

        response = await client.patch(
            f"/tasks/{non_existent_id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 404

    async def test_update_task_unauthorized_org(
        self,
        client: AsyncClient,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a task in unauthorized org fails."""
        # Create a task in a different org
        other_org = KOrganization(
            id=get_test_org_id(),
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        task = KTask(
            id=get_test_task_id(other_org.id),
            summary="Other task summary",
            org_id=other_org.id,
            team_id=test_team.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        # Try to update with unauthorized org (user is not member of other_org)
        update_data = {"summary": "Updated summary"}
        response = await client.patch(
            f"/tasks/{task.id}?org_id={other_org.id}",
            json=update_data,
        )
        assert response.status_code == 403


class TestDeleteTask:
    """Test suite for DELETE /tasks/{task_id} endpoint."""

    async def test_delete_task_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting a task."""
        task = KTask(
            id=get_test_task_id(test_organization.id),
            summary="Task to delete",
            org_id=test_organization.id,
            team_id=test_team.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        response = await client.delete(
            f"/tasks/{task.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204

        # Verify task is deleted
        get_response = await client.get(
            f"/tasks/{task.id}?org_id={test_organization.id}"
        )
        assert get_response.status_code == 404

    async def test_delete_task_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test deleting a non-existent task."""
        non_existent_id = uuid7()

        response = await client.delete(
            f"/tasks/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    async def test_delete_task_unauthorized_org(
        self,
        client: AsyncClient,
        test_team: KTeam,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a task in unauthorized org fails."""
        # Create a task in a different org
        other_org = KOrganization(
            id=get_test_org_id(),
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        task = KTask(
            id=get_test_task_id(other_org.id),
            summary="Other task summary",
            org_id=other_org.id,
            team_id=test_team.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        # Try to delete with unauthorized org (user is not member of other_org)
        response = await client.delete(f"/tasks/{task.id}?org_id={other_org.id}")
        assert response.status_code == 403
