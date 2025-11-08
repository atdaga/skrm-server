"""Unit tests for task owner management endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganizationPrincipal, KPrincipal, KTask, KTaskOwner, KTeam
from app.routes.v1.task_owners import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with task_owners router included."""
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
        name="Test Task",
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
        username="testowner",
        primary_email="testowner@example.com",
        first_name="Test",
        last_name="Owner",
        display_name="Test Owner",
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


class TestAddTaskOwner:
    """Test suite for POST /tasks/{task_id}/owners endpoint."""

    @pytest.mark.asyncio
    async def test_add_task_owner_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new owner to a task."""
        owner_data = {
            "principal_id": str(principal.id),
            "role": "lead",
            "meta": {
                "responsibility": "implementation",
                "allocation": 80,
            },
        }

        response = await client.post(f"/tasks/{task.id}/owners", json=owner_data)

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "lead"
        assert data["meta"] == {
            "responsibility": "implementation",
            "allocation": 80,
        }
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_add_task_owner_minimal_fields(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
    ):
        """Test adding an owner with only required fields."""
        owner_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/tasks/{task.id}/owners", json=owner_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_task_owner_duplicate(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
    ):
        """Test that adding the same owner twice fails."""
        owner_data = {
            "principal_id": str(principal.id),
            "role": "lead",
        }

        # Add owner first time
        response = await client.post(f"/tasks/{task.id}/owners", json=owner_data)
        assert response.status_code == 201

        # Try to add the same owner again
        response = await client.post(f"/tasks/{task.id}/owners", json=owner_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_task_owner_nonexistent_task(
        self,
        client: AsyncClient,
        principal: KPrincipal,
    ):
        """Test that adding an owner to a non-existent task fails."""
        non_existent_task_id = uuid4()
        owner_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/tasks/{non_existent_task_id}/owners", json=owner_data
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_task_owner_nonexistent_principal(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test that adding a non-existent principal fails."""
        non_existent_principal_id = uuid4()
        owner_data = {"principal_id": str(non_existent_principal_id)}

        response = await client.post(f"/tasks/{task.id}/owners", json=owner_data)
        assert response.status_code == 404


class TestListTaskOwners:
    """Test suite for GET /tasks/{task_id}/owners endpoint."""

    @pytest.mark.asyncio
    async def test_list_task_owners_empty(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test listing owners when none exist."""
        response = await client.get(f"/tasks/{task.id}/owners")

        assert response.status_code == 200
        data = response.json()
        assert data["owners"] == []

    @pytest.mark.asyncio
    async def test_list_task_owners_multiple(
        self,
        client: AsyncClient,
        task: KTask,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple owners."""
        # Create multiple principals
        principal1 = KPrincipal(
            username="owner1",
            primary_email="owner1@example.com",
            first_name="Owner",
            last_name="One",
            display_name="Owner One",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        principal2 = KPrincipal(
            username="owner2",
            primary_email="owner2@example.com",
            first_name="Owner",
            last_name="Two",
            display_name="Owner Two",
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

        # Add both principals as owners to the task
        task_owner1 = KTaskOwner(
            task_id=task.id,
            principal_id=principal1.id,
            org_id=test_org_id,
            role="lead",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        task_owner2 = KTaskOwner(
            task_id=task.id,
            principal_id=principal2.id,
            org_id=test_org_id,
            role="backup",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([task_owner1, task_owner2])
        await async_session.commit()

        response = await client.get(f"/tasks/{task.id}/owners")

        assert response.status_code == 200
        data = response.json()
        assert len(data["owners"]) == 2
        owner_roles = [o["role"] for o in data["owners"]]
        assert "lead" in owner_roles
        assert "backup" in owner_roles

    @pytest.mark.asyncio
    async def test_list_task_owners_nonexistent_task(
        self,
        client: AsyncClient,
    ):
        """Test listing owners for a non-existent task."""
        non_existent_id = uuid4()

        response = await client.get(f"/tasks/{non_existent_id}/owners")
        assert response.status_code == 404


class TestGetTaskOwner:
    """Test suite for GET /tasks/{task_id}/owners/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_owner_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a task owner."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead",
            meta={"allocation": 100},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_owner)
        await async_session.commit()
        await async_session.refresh(task_owner)

        response = await client.get(f"/tasks/{task.id}/owners/{principal.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(task.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "lead"
        assert data["meta"] == {"allocation": 100}

    @pytest.mark.asyncio
    async def test_get_task_owner_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test getting a non-existent task owner."""
        non_existent_principal_id = uuid4()

        response = await client.get(
            f"/tasks/{task.id}/owners/{non_existent_principal_id}"
        )
        assert response.status_code == 404


class TestUpdateTaskOwner:
    """Test suite for PATCH /tasks/{task_id}/owners/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_owner_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully updating a task owner."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="old_role",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_owner)
        await async_session.commit()
        await async_session.refresh(task_owner)

        update_data = {
            "role": "new_role",
            "meta": {"new": "data", "status": "updated"},
        }

        response = await client.patch(
            f"/tasks/{task.id}/owners/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "new_role"
        assert data["meta"] == {"new": "data", "status": "updated"}

    @pytest.mark.asyncio
    async def test_update_task_owner_partial(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a task owner."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="original_role",
            meta={"original": "meta"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_owner)
        await async_session.commit()
        await async_session.refresh(task_owner)

        update_data = {"role": "updated_role"}

        response = await client.patch(
            f"/tasks/{task.id}/owners/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "updated_role"
        assert data["meta"] == {"original": "meta"}  # Unchanged

    @pytest.mark.asyncio
    async def test_update_task_owner_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test updating a non-existent task owner."""
        non_existent_principal_id = uuid4()
        update_data = {"role": "new_role"}

        response = await client.patch(
            f"/tasks/{task.id}/owners/{non_existent_principal_id}",
            json=update_data,
        )
        assert response.status_code == 404


class TestRemoveTaskOwner:
    """Test suite for DELETE /tasks/{task_id}/owners/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_task_owner_success(
        self,
        client: AsyncClient,
        task: KTask,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing an owner from a task."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="to_remove",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(task_owner)
        await async_session.commit()
        await async_session.refresh(task_owner)

        response = await client.delete(f"/tasks/{task.id}/owners/{principal.id}")

        assert response.status_code == 204

        # Verify task owner is deleted
        get_response = await client.get(f"/tasks/{task.id}/owners/{principal.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_task_owner_not_found(
        self,
        client: AsyncClient,
        task: KTask,
    ):
        """Test removing a non-existent task owner."""
        non_existent_principal_id = uuid4()

        response = await client.delete(
            f"/tasks/{task.id}/owners/{non_existent_principal_id}"
        )
        assert response.status_code == 404
