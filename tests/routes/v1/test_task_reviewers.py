"""Unit tests for task reviewer management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganizationPrincipal, KPrincipal, KTask, KTaskReviewer, KTeam
from app.routes.v1.task_reviewers import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with task_reviewers router included."""
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
async def principal(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KPrincipal:
    """Create a test principal."""
    principal = KPrincipal(
        username="testreviewer",
        primary_email="testreviewer@example.com",
        first_name="Test",
        last_name="Reviewer",
        display_name="Test Reviewer",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()
    await async_session.refresh(principal)

    # Add principal to organization
    org_principal = KOrganizationPrincipal(
        org_id=test_org_id,
        principal_id=principal.id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(org_principal)
    await async_session.commit()

    return principal


class TestAddTaskReviewer:
    """Test suite for POST /tasks/{task_id}/reviewers endpoint."""

    @pytest.mark.asyncio
    async def test_add_task_reviewer_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new reviewer to a task."""
        reviewer_data = {
            "principal_id": str(principal.id),
            "role": "technical",
            "meta": {
                "expertise": "security",
                "review_type": "code",
            },
        }

        response = await client.post(f"/tasks/{task.id}/reviewers", json=reviewer_data)

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "technical"
        assert data["meta"] == {
            "expertise": "security",
            "review_type": "code",
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_add_task_reviewer_minimal_fields(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
    ):
        """Test adding a reviewer with only required fields."""
        reviewer_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/tasks/{task.id}/reviewers", json=reviewer_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_task_reviewer_duplicate(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
    ):
        """Test that adding the same reviewer twice fails."""
        reviewer_data = {
            "principal_id": str(principal.id),
            "role": "technical",
        }

        # Add reviewer first time
        response = await client.post(f"/tasks/{task.id}/reviewers", json=reviewer_data)
        assert response.status_code == 201

        # Try to add the same reviewer again
        response = await client.post(f"/tasks/{task.id}/reviewers", json=reviewer_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_task_reviewer_nonexistent_task(
        self,
        client: AsyncClient,
        principal: KPrincipal,
    ):
        """Test that adding a reviewer to a non-existent task fails."""
        non_existent_task_id = uuid7()
        reviewer_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/tasks/{non_existent_task_id}/reviewers", json=reviewer_data
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_task_reviewer_nonexistent_principal(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test that adding a non-existent principal fails."""
        non_existent_principal_id = uuid7()
        reviewer_data = {"principal_id": str(non_existent_principal_id)}

        response = await client.post(f"/tasks/{task.id}/reviewers", json=reviewer_data)
        assert response.status_code == 404


class TestListTaskReviewers:
    """Test suite for GET /tasks/{task_id}/reviewers endpoint."""

    @pytest.mark.asyncio
    async def test_list_task_reviewers_empty(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test listing reviewers when none exist."""
        response = await client.get(f"/tasks/{task.id}/reviewers")

        assert response.status_code == 200
        data = response.json()
        assert data["reviewers"] == []

    @pytest.mark.asyncio
    async def test_list_task_reviewers_multiple(
        self,
        client: AsyncClient,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple reviewers."""
        # Create multiple principals
        principal1 = KPrincipal(
            username="reviewer1",
            primary_email="reviewer1@example.com",
            first_name="Reviewer",
            last_name="One",
            display_name="Reviewer One",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        principal2 = KPrincipal(
            username="reviewer2",
            primary_email="reviewer2@example.com",
            first_name="Reviewer",
            last_name="Two",
            display_name="Reviewer Two",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([principal1, principal2])
        await async_session.commit()
        await async_session.refresh(principal1)
        await async_session.refresh(principal2)

        # Add principals to organization
        org_principal1 = KOrganizationPrincipal(
            org_id=test_org_id,
            principal_id=principal1.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        org_principal2 = KOrganizationPrincipal(
            org_id=test_org_id,
            principal_id=principal2.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([org_principal1, org_principal2])
        await async_session.commit()

        # Add both principals as reviewers to the task
        task_reviewer1 = KTaskReviewer(
            task_id=task.id,
            principal_id=principal1.id,
            org_id=test_org_id,
            role="technical",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task_reviewer2 = KTaskReviewer(
            task_id=task.id,
            principal_id=principal2.id,
            org_id=test_org_id,
            role="functional",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task_reviewer1, task_reviewer2])
        await async_session.commit()

        response = await client.get(f"/tasks/{task.id}/reviewers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["reviewers"]) == 2
        reviewer_roles = [r["role"] for r in data["reviewers"]]
        assert "technical" in reviewer_roles
        assert "functional" in reviewer_roles

    @pytest.mark.asyncio
    async def test_list_task_reviewers_nonexistent_task(
        self,
        client: AsyncClient,
    ):
        """Test listing reviewers for a non-existent task."""
        non_existent_id = uuid7()

        response = await client.get(f"/tasks/{non_existent_id}/reviewers")
        assert response.status_code == 404


class TestGetTaskReviewer:
    """Test suite for GET /tasks/{task_id}/reviewers/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_reviewer_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a task reviewer."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="technical",
            meta={"expertise": "security"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_reviewer)
        await async_session.commit()
        await async_session.refresh(task_reviewer)

        response = await client.get(f"/tasks/{task.id}/reviewers/{principal.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "technical"
        assert data["meta"] == {"expertise": "security"}

    @pytest.mark.asyncio
    async def test_get_task_reviewer_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test getting a non-existent task reviewer."""
        non_existent_principal_id = uuid7()

        response = await client.get(
            f"/tasks/{task.id}/reviewers/{non_existent_principal_id}"
        )
        assert response.status_code == 404


class TestUpdateTaskReviewer:
    """Test suite for PATCH /tasks/{task_id}/reviewers/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_reviewer_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a task reviewer."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_reviewer)
        await async_session.commit()
        await async_session.refresh(task_reviewer)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/tasks/{task.id}/reviewers/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    @pytest.mark.asyncio
    async def test_update_task_reviewer_partial(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a task reviewer."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_reviewer)
        await async_session.commit()
        await async_session.refresh(task_reviewer)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/tasks/{task.id}/reviewers/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    @pytest.mark.asyncio
    async def test_update_task_reviewer_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test updating a non-existent task reviewer."""
        non_existent_principal_id = uuid7()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/tasks/{task.id}/reviewers/{non_existent_principal_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveTaskReviewer:
    """Test suite for DELETE /tasks/{task_id}/reviewers/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_task_reviewer_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a reviewer from a task."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_reviewer)
        await async_session.commit()
        await async_session.refresh(task_reviewer)

        response = await client.delete(f"/tasks/{task.id}/reviewers/{principal.id}")

        assert response.status_code == 204

        # Verify task reviewer is deleted
        get_response = await client.get(f"/tasks/{task.id}/reviewers/{principal.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_task_reviewer_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test removing a non-existent task reviewer."""
        non_existent_principal_id = uuid7()

        response = await client.delete(
            f"/tasks/{task.id}/reviewers/{non_existent_principal_id}"
        )
        assert response.status_code == 404
