"""Unit tests for sprint task management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KSprint, KSprintTask, KTask, KTeam
from app.routes.v1.sprint_tasks import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with sprint_tasks router included."""
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
        name="Test Team",
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(team)
    await async_session.commit()
    await async_session.refresh(team)
    return team


@pytest.fixture
async def task(
    async_session: AsyncSession, team: KTeam, test_org_id: UUID, test_user_id: UUID
) -> KTask:
    """Create a test task."""
    task = KTask(
        summary="Test task summary",
        team_id=team.id,
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(task)
    await async_session.commit()
    await async_session.refresh(task)
    return task


class TestAddSprintTask:
    """Test suite for POST /sprints/{sprint_id}/tasks endpoint."""

    async def test_add_sprint_task_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new task to a sprint."""
        task_data = {
            "task_id": str(task.id),
            "role": "primary",
            "meta": {
                "priority": "high",
                "estimated_hours": 8,
            },
        }

        response = await client.post(f"/sprints/{sprint.id}/tasks", json=task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["sprint_id"] == str(sprint.id)
        assert data["task_id"] == str(task.id)
        assert data["role"] == "primary"
        assert data["meta"] == {
            "priority": "high",
            "estimated_hours": 8,
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_add_sprint_task_minimal_fields(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
    ):
        """Test adding a task with only required fields."""
        task_data = {"task_id": str(task.id)}

        response = await client.post(f"/sprints/{sprint.id}/tasks", json=task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    async def test_add_sprint_task_duplicate(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
    ):
        """Test that adding the same task twice fails."""
        task_data = {"task_id": str(task.id), "role": "primary"}

        # Add task first time
        response = await client.post(f"/sprints/{sprint.id}/tasks", json=task_data)
        assert response.status_code == 201

        # Try to add the same task again
        response = await client.post(f"/sprints/{sprint.id}/tasks", json=task_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_add_sprint_task_nonexistent_sprint(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test that adding a task to a non-existent sprint fails."""
        non_existent_sprint_id = uuid7()
        task_data = {"task_id": str(task.id)}

        response = await client.post(
            f"/sprints/{non_existent_sprint_id}/tasks", json=task_data
        )
        assert response.status_code == 404

    async def test_add_sprint_task_nonexistent_task(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test that adding a non-existent task fails."""
        non_existent_task_id = uuid7()
        task_data = {"task_id": str(non_existent_task_id)}

        response = await client.post(f"/sprints/{sprint.id}/tasks", json=task_data)
        assert response.status_code == 404


class TestListSprintTasks:
    """Test suite for GET /sprints/{sprint_id}/tasks endpoint."""

    async def test_list_sprint_tasks_empty(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test listing tasks when none exist."""
        response = await client.get(f"/sprints/{sprint.id}/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []

    async def test_list_sprint_tasks_multiple(
        self,
        client: AsyncClient,
        sprint: KSprint,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
        team: KTeam,
    ):
        """Test listing multiple tasks."""
        # Create multiple tasks
        task1 = KTask(
            summary="Task One",
            team_id=team.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task2 = KTask(
            summary="Task Two",
            team_id=team.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task1, task2])
        await async_session.commit()
        await async_session.refresh(task1)
        await async_session.refresh(task2)

        # Add both tasks to the sprint
        sprint_task1 = KSprintTask(
            sprint_id=sprint.id,
            task_id=task1.id,
            org_id=test_org_id,
            role="primary",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        sprint_task2 = KSprintTask(
            sprint_id=sprint.id,
            task_id=task2.id,
            org_id=test_org_id,
            role="secondary",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([sprint_task1, sprint_task2])
        await async_session.commit()

        response = await client.get(f"/sprints/{sprint.id}/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        task_roles = [t["role"] for t in data["tasks"]]
        assert "primary" in task_roles
        assert "secondary" in task_roles

    async def test_list_sprint_tasks_nonexistent_sprint(
        self,
        client: AsyncClient,
    ):
        """Test listing tasks for a non-existent sprint."""
        non_existent_id = uuid7()

        response = await client.get(f"/sprints/{non_existent_id}/tasks")
        assert response.status_code == 404


class TestGetSprintTask:
    """Test suite for GET /sprints/{sprint_id}/tasks/{task_id} endpoint."""

    async def test_get_sprint_task_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a sprint task."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="primary",
            meta={"priority": "high"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_task)
        await async_session.commit()
        await async_session.refresh(sprint_task)

        response = await client.get(f"/sprints/{sprint.id}/tasks/{task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["sprint_id"] == str(sprint.id)
        assert data["task_id"] == str(task.id)
        assert data["role"] == "primary"
        assert data["meta"] == {"priority": "high"}

    async def test_get_sprint_task_not_found(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test getting a non-existent sprint task."""
        non_existent_task_id = uuid7()

        response = await client.get(
            f"/sprints/{sprint.id}/tasks/{non_existent_task_id}"
        )
        assert response.status_code == 404


class TestUpdateSprintTask:
    """Test suite for PATCH /sprints/{sprint_id}/tasks/{task_id} endpoint."""

    async def test_update_sprint_task_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a sprint task."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_task)
        await async_session.commit()
        await async_session.refresh(sprint_task)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/sprints/{sprint.id}/tasks/{task.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    async def test_update_sprint_task_partial(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a sprint task."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_task)
        await async_session.commit()
        await async_session.refresh(sprint_task)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/sprints/{sprint.id}/tasks/{task.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    async def test_update_sprint_task_not_found(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test updating a non-existent sprint task."""
        non_existent_task_id = uuid7()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/sprints/{sprint.id}/tasks/{non_existent_task_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveSprintTask:
    """Test suite for DELETE /sprints/{sprint_id}/tasks/{task_id} endpoint."""

    async def test_remove_sprint_task_success(
        self,
        client: AsyncClient,
        sprint: KSprint,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a task from a sprint."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint_task)
        await async_session.commit()
        await async_session.refresh(sprint_task)

        response = await client.delete(f"/sprints/{sprint.id}/tasks/{task.id}")

        assert response.status_code == 204

        # Verify sprint task is deleted
        get_response = await client.get(f"/sprints/{sprint.id}/tasks/{task.id}")
        assert get_response.status_code == 404

    async def test_remove_sprint_task_not_found(
        self,
        client: AsyncClient,
        sprint: KSprint,
    ):
        """Test removing a non-existent sprint task."""
        non_existent_task_id = uuid7()

        response = await client.delete(
            f"/sprints/{sprint.id}/tasks/{non_existent_task_id}"
        )
        assert response.status_code == 404
