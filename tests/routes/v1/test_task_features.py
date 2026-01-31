"""Unit tests for task feature management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KFeature, KTask, KTaskFeature, KTeam
from app.models.k_feature import FeatureType
from app.routes.v1.task_features import feature_tasks_router, router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with task_features router included."""
    app_with_overrides.include_router(router)
    app_with_overrides.include_router(feature_tasks_router)
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
async def feature(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KFeature:
    """Create a test feature."""
    feature = KFeature(
        name="User Authentication",
        org_id=test_org_id,
        feature_type=FeatureType.PRODUCT,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(feature)
    await async_session.commit()
    await async_session.refresh(feature)
    return feature


class TestAddTaskFeature:
    """Test suite for POST /tasks/{task_id}/features endpoint."""

    async def test_add_task_feature_success(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new feature to a task."""
        feature_data = {
            "feature_id": str(feature.id),
            "role": "implements",
            "meta": {
                "completion": 50,
                "priority": "high",
            },
        }

        response = await client.post(f"/tasks/{task.id}/features", json=feature_data)

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["feature_id"] == str(feature.id)
        assert data["role"] == "implements"
        assert data["meta"] == {
            "completion": 50,
            "priority": "high",
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_add_task_feature_minimal_fields(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
    ):
        """Test adding a feature with only required fields."""
        feature_data = {"feature_id": str(feature.id)}

        response = await client.post(f"/tasks/{task.id}/features", json=feature_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    async def test_add_task_feature_duplicate(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
    ):
        """Test that adding the same feature twice fails."""
        feature_data = {
            "feature_id": str(feature.id),
            "role": "implements",
        }

        # Add feature first time
        response = await client.post(f"/tasks/{task.id}/features", json=feature_data)
        assert response.status_code == 201

        # Try to add the same feature again
        response = await client.post(f"/tasks/{task.id}/features", json=feature_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_add_task_feature_nonexistent_task(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test that adding a feature to a non-existent task fails."""
        non_existent_task_id = uuid7()
        feature_data = {"feature_id": str(feature.id)}

        response = await client.post(
            f"/tasks/{non_existent_task_id}/features", json=feature_data
        )
        assert response.status_code == 404

    async def test_add_task_feature_nonexistent_feature(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test that adding a non-existent feature fails."""
        non_existent_feature_id = uuid7()
        feature_data = {"feature_id": str(non_existent_feature_id)}

        response = await client.post(f"/tasks/{task.id}/features", json=feature_data)
        assert response.status_code == 404


class TestListTaskFeatures:
    """Test suite for GET /tasks/{task_id}/features endpoint."""

    async def test_list_task_features_empty(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test listing features when none exist."""
        response = await client.get(f"/tasks/{task.id}/features")

        assert response.status_code == 200
        data = response.json()
        assert data["features"] == []

    async def test_list_task_features_multiple(
        self,
        client: AsyncClient,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple features."""
        # Create multiple features
        feature1 = KFeature(
            name="Authentication",
            org_id=test_org_id,
            feature_type=FeatureType.PRODUCT,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        feature2 = KFeature(
            name="Dashboard",
            org_id=test_org_id,
            feature_type=FeatureType.PRODUCT,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([feature1, feature2])
        await async_session.commit()
        await async_session.refresh(feature1)
        await async_session.refresh(feature2)

        # Add both features to the task
        task_feature1 = KTaskFeature(
            task_id=task.id,
            feature_id=feature1.id,
            org_id=test_org_id,
            role="implements",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task_feature2 = KTaskFeature(
            task_id=task.id,
            feature_id=feature2.id,
            org_id=test_org_id,
            role="extends",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task_feature1, task_feature2])
        await async_session.commit()

        response = await client.get(f"/tasks/{task.id}/features")

        assert response.status_code == 200
        data = response.json()
        assert len(data["features"]) == 2
        feature_roles = [f["role"] for f in data["features"]]
        assert "implements" in feature_roles
        assert "extends" in feature_roles

    async def test_list_task_features_nonexistent_task(
        self,
        client: AsyncClient,
    ):
        """Test listing features for a non-existent task."""
        non_existent_id = uuid7()

        response = await client.get(f"/tasks/{non_existent_id}/features")
        assert response.status_code == 404


class TestGetTaskFeature:
    """Test suite for GET /tasks/{task_id}/features/{feature_id} endpoint."""

    async def test_get_task_feature_success(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a task feature."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="implements",
            meta={"priority": "high"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_feature)
        await async_session.commit()
        await async_session.refresh(task_feature)

        response = await client.get(f"/tasks/{task.id}/features/{feature.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["feature_id"] == str(feature.id)
        assert data["role"] == "implements"
        assert data["meta"] == {"priority": "high"}

    async def test_get_task_feature_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test getting a non-existent task feature."""
        non_existent_feature_id = uuid7()

        response = await client.get(
            f"/tasks/{task.id}/features/{non_existent_feature_id}"
        )
        assert response.status_code == 404


class TestUpdateTaskFeature:
    """Test suite for PATCH /tasks/{task_id}/features/{feature_id} endpoint."""

    async def test_update_task_feature_success(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a task feature."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_feature)
        await async_session.commit()
        await async_session.refresh(task_feature)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/tasks/{task.id}/features/{feature.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    async def test_update_task_feature_partial(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a task feature."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_feature)
        await async_session.commit()
        await async_session.refresh(task_feature)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/tasks/{task.id}/features/{feature.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    async def test_update_task_feature_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test updating a non-existent task feature."""
        non_existent_feature_id = uuid7()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/tasks/{task.id}/features/{non_existent_feature_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveTaskFeature:
    """Test suite for DELETE /tasks/{task_id}/features/{feature_id} endpoint."""

    async def test_remove_task_feature_success(
        self,
        client: AsyncClient,
        task: KTask,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a feature from a task."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_feature)
        await async_session.commit()
        await async_session.refresh(task_feature)

        response = await client.delete(f"/tasks/{task.id}/features/{feature.id}")

        assert response.status_code == 204

        # Verify task feature is deleted
        get_response = await client.get(f"/tasks/{task.id}/features/{feature.id}")
        assert get_response.status_code == 404

    async def test_remove_task_feature_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test removing a non-existent task feature."""
        non_existent_feature_id = uuid7()

        response = await client.delete(
            f"/tasks/{task.id}/features/{non_existent_feature_id}"
        )
        assert response.status_code == 404


class TestListTasksByFeature:
    """Test suite for GET /tasks/feature/{feature_id} endpoint."""

    async def test_list_tasks_by_feature_empty(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test listing tasks when none are linked to the feature (default detail=true)."""
        response = await client.get(f"/tasks/feature/{feature.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []

    async def test_list_tasks_by_feature_detail_true(
        self,
        client: AsyncClient,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing tasks with detail=true returns full task objects."""
        # Create a team for the tasks
        team = KTeam(
            name="Feature Team",
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        # Create multiple tasks
        task1 = KTask(
            summary="Task one",
            team_id=team.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task2 = KTask(
            summary="Task two",
            team_id=team.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task1, task2])
        await async_session.commit()
        await async_session.refresh(task1)
        await async_session.refresh(task2)

        # Link both tasks to the feature
        tf1 = KTaskFeature(
            task_id=task1.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="implements",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        tf2 = KTaskFeature(
            task_id=task2.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="tests",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([tf1, tf2])
        await async_session.commit()

        response = await client.get(f"/tasks/feature/{feature.id}?detail=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        task_ids = {t["id"] for t in data["tasks"]}
        assert str(task1.id) in task_ids
        assert str(task2.id) in task_ids
        # Verify full task shape
        for t in data["tasks"]:
            assert "summary" in t
            assert "status" in t
            assert "team_id" in t
            assert "created" in t
            assert "created_by" in t

    async def test_list_tasks_by_feature_detail_false(
        self,
        client: AsyncClient,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing tasks with detail=false returns junction records."""
        # Create a team for the tasks
        team = KTeam(
            name="Feature Team",
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(team)
        await async_session.commit()
        await async_session.refresh(team)

        # Create multiple tasks
        task1 = KTask(
            summary="Task one",
            team_id=team.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task2 = KTask(
            summary="Task two",
            team_id=team.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task1, task2])
        await async_session.commit()
        await async_session.refresh(task1)
        await async_session.refresh(task2)

        # Link both tasks to the feature
        tf1 = KTaskFeature(
            task_id=task1.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="implements",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        tf2 = KTaskFeature(
            task_id=task2.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="tests",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([tf1, tf2])
        await async_session.commit()

        response = await client.get(f"/tasks/feature/{feature.id}?detail=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data["features"]) == 2
        task_ids = {f["task_id"] for f in data["features"]}
        assert str(task1.id) in task_ids
        assert str(task2.id) in task_ids
        # Verify junction record shape
        for f in data["features"]:
            assert "task_id" in f
            assert "feature_id" in f
            assert "role" in f

    async def test_list_tasks_by_feature_nonexistent(
        self,
        client: AsyncClient,
    ):
        """Test listing tasks for a non-existent feature returns 404."""
        non_existent_id = uuid7()

        response = await client.get(f"/tasks/feature/{non_existent_id}")
        assert response.status_code == 404
