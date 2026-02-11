"""Unit tests for task deployment environment management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KDeploymentEnv, KTask, KTaskDeploymentEnv, KTeam
from app.routes.v1.task_deployment_envs import router
from tests.conftest import get_test_task_id


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with task_deployment_envs router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


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
        id=get_test_task_id(test_org_id),
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


@pytest.fixture
async def deployment_env(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KDeploymentEnv:
    """Create a test deployment environment."""
    deployment_env = KDeploymentEnv(
        name="Production",
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(deployment_env)
    await async_session.commit()
    await async_session.refresh(deployment_env)
    return deployment_env


class TestAddTaskDeploymentEnv:
    """Test suite for POST /tasks/{task_id}/deployment_envs endpoint."""

    async def test_add_task_deployment_env_success(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new deployment environment to a task."""
        deployment_env_data = {
            "deployment_env_id": str(deployment_env.id),
            "role": "target",
            "meta": {
                "auto_deploy": True,
                "priority": 1,
            },
        }

        response = await client.post(
            f"/tasks/{task.id}/deployment_envs", json=deployment_env_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["deployment_env_id"] == str(deployment_env.id)
        assert data["role"] == "target"
        assert data["meta"] == {
            "auto_deploy": True,
            "priority": 1,
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_add_task_deployment_env_minimal_fields(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
    ):
        """Test adding a deployment environment with only required fields."""
        deployment_env_data = {"deployment_env_id": str(deployment_env.id)}

        response = await client.post(
            f"/tasks/{task.id}/deployment_envs", json=deployment_env_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    async def test_add_task_deployment_env_duplicate(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
    ):
        """Test that adding the same deployment environment twice fails."""
        deployment_env_data = {
            "deployment_env_id": str(deployment_env.id),
            "role": "target",
        }

        # Add deployment environment first time
        response = await client.post(
            f"/tasks/{task.id}/deployment_envs", json=deployment_env_data
        )
        assert response.status_code == 201

        # Try to add the same deployment environment again
        response = await client.post(
            f"/tasks/{task.id}/deployment_envs", json=deployment_env_data
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_add_task_deployment_env_nonexistent_task(
        self,
        client: AsyncClient,
        deployment_env: KDeploymentEnv,
    ):
        """Test that adding a deployment environment to a non-existent task fails."""
        non_existent_task_id = uuid7()
        deployment_env_data = {"deployment_env_id": str(deployment_env.id)}

        response = await client.post(
            f"/tasks/{non_existent_task_id}/deployment_envs", json=deployment_env_data
        )
        assert response.status_code == 404

    async def test_add_task_deployment_env_nonexistent_deployment_env(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test that adding a non-existent deployment environment fails."""
        non_existent_env_id = uuid7()
        deployment_env_data = {"deployment_env_id": str(non_existent_env_id)}

        response = await client.post(
            f"/tasks/{task.id}/deployment_envs", json=deployment_env_data
        )
        assert response.status_code == 404


class TestListTaskDeploymentEnvs:
    """Test suite for GET /tasks/{task_id}/deployment_envs endpoint."""

    async def test_list_task_deployment_envs_empty(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test listing deployment environments when none exist."""
        response = await client.get(f"/tasks/{task.id}/deployment_envs")

        assert response.status_code == 200
        data = response.json()
        assert data["deployment_envs"] == []

    async def test_list_task_deployment_envs_multiple(
        self,
        client: AsyncClient,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple deployment environments."""
        # Create multiple deployment environments
        env1 = KDeploymentEnv(
            name="Staging",
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        env2 = KDeploymentEnv(
            name="Production",
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([env1, env2])
        await async_session.commit()
        await async_session.refresh(env1)
        await async_session.refresh(env2)

        # Add both deployment environments to the task
        task_env1 = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=env1.id,
            org_id=test_org_id,
            role="staging",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task_env2 = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=env2.id,
            org_id=test_org_id,
            role="production",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task_env1, task_env2])
        await async_session.commit()

        response = await client.get(f"/tasks/{task.id}/deployment_envs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["deployment_envs"]) == 2
        env_roles = [e["role"] for e in data["deployment_envs"]]
        assert "staging" in env_roles
        assert "production" in env_roles

    async def test_list_task_deployment_envs_nonexistent_task(
        self,
        client: AsyncClient,
    ):
        """Test listing deployment environments for a non-existent task."""
        non_existent_id = uuid7()

        response = await client.get(f"/tasks/{non_existent_id}/deployment_envs")
        assert response.status_code == 404


class TestGetTaskDeploymentEnv:
    """Test suite for GET /tasks/{task_id}/deployment_envs/{deployment_env_id} endpoint."""

    async def test_get_task_deployment_env_success(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a task deployment environment."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="primary",
            meta={"priority": "high"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_deployment_env)
        await async_session.commit()
        await async_session.refresh(task_deployment_env)

        response = await client.get(
            f"/tasks/{task.id}/deployment_envs/{deployment_env.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["deployment_env_id"] == str(deployment_env.id)
        assert data["role"] == "primary"
        assert data["meta"] == {"priority": "high"}

    async def test_get_task_deployment_env_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test getting a non-existent task deployment environment."""
        non_existent_env_id = uuid7()

        response = await client.get(
            f"/tasks/{task.id}/deployment_envs/{non_existent_env_id}"
        )
        assert response.status_code == 404


class TestUpdateTaskDeploymentEnv:
    """Test suite for PATCH /tasks/{task_id}/deployment_envs/{deployment_env_id} endpoint."""

    async def test_update_task_deployment_env_success(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a task deployment environment."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_deployment_env)
        await async_session.commit()
        await async_session.refresh(task_deployment_env)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/tasks/{task.id}/deployment_envs/{deployment_env.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    async def test_update_task_deployment_env_partial(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a task deployment environment."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_deployment_env)
        await async_session.commit()
        await async_session.refresh(task_deployment_env)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/tasks/{task.id}/deployment_envs/{deployment_env.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    async def test_update_task_deployment_env_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test updating a non-existent task deployment environment."""
        non_existent_env_id = uuid7()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/tasks/{task.id}/deployment_envs/{non_existent_env_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveTaskDeploymentEnv:
    """Test suite for DELETE /tasks/{task_id}/deployment_envs/{deployment_env_id} endpoint."""

    async def test_remove_task_deployment_env_success(
        self,
        client: AsyncClient,
        task: KTask,
        deployment_env: KDeploymentEnv,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a deployment environment from a task."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_deployment_env)
        await async_session.commit()
        await async_session.refresh(task_deployment_env)

        response = await client.delete(
            f"/tasks/{task.id}/deployment_envs/{deployment_env.id}"
        )

        assert response.status_code == 204

        # Verify task deployment environment is deleted
        get_response = await client.get(
            f"/tasks/{task.id}/deployment_envs/{deployment_env.id}"
        )
        assert get_response.status_code == 404

    async def test_remove_task_deployment_env_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test removing a non-existent task deployment environment."""
        non_existent_env_id = uuid7()

        response = await client.delete(
            f"/tasks/{task.id}/deployment_envs/{non_existent_env_id}"
        )
        assert response.status_code == 404
