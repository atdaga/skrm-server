"""Unit tests for sprint management endpoints."""

from datetime import datetime
from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KSprint
from app.models.k_sprint import SprintStatus
from app.routes.v1.sprints import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with sprints router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestCreateSprint:
    """Test suite for POST /sprints endpoint."""

    @pytest.mark.asyncio
    async def test_create_sprint_success(
        self,
        client: AsyncClient,
        test_organization,
        test_user_id: UUID,
    ):
        """Test successfully creating a new sprint."""
        sprint_data = {
            "title": "Sprint 1 - Q1 2024",
            "status": "Active",
            "end_ts": "2024-03-31T23:59:59",
            "meta": {"goal": "Complete authentication", "velocity": 42},
        }

        response = await client.post(
            f"/sprints?org_id={test_organization.id}", json=sprint_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Sprint 1 - Q1 2024"
        assert data["status"] == "Active"
        assert data["meta"] == {"goal": "Complete authentication", "velocity": 42}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_create_sprint_minimal_fields(
        self,
        client: AsyncClient,
        test_organization,
        test_user_id: UUID,
    ):
        """Test creating a sprint with only required fields."""
        sprint_data = {}

        response = await client.post(
            f"/sprints?org_id={test_organization.id}", json=sprint_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None
        assert data["status"] == "Backlog"
        assert data["end_ts"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_sprint_unauthorized_org(
        self, client: AsyncClient, test_user_id: UUID
    ):
        """Test that creating a sprint in unauthorized org fails."""
        unauthorized_org_id = uuid7()
        sprint_data = {"title": "Test Sprint"}

        response = await client.post(
            f"/sprints?org_id={unauthorized_org_id}", json=sprint_data
        )
        assert response.status_code == 403


class TestListSprints:
    """Test suite for GET /sprints endpoint."""

    @pytest.mark.asyncio
    async def test_list_sprints_empty(self, client: AsyncClient, test_organization):
        """Test listing sprints when none exist."""
        response = await client.get(f"/sprints?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["sprints"] == []

    @pytest.mark.asyncio
    async def test_list_sprints_multiple(
        self,
        client: AsyncClient,
        test_organization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple sprints."""
        # Create multiple sprints
        sprints = [
            KSprint(
                title="Sprint Alpha",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
            KSprint(
                title="Sprint Beta",
                status=SprintStatus.ACTIVE,
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
        ]

        for sprint in sprints:
            async_session.add(sprint)
        await async_session.commit()

        response = await client.get(f"/sprints?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sprints"]) == 2
        sprint_titles = [s["title"] for s in data["sprints"]]
        assert "Sprint Alpha" in sprint_titles
        assert "Sprint Beta" in sprint_titles

    @pytest.mark.asyncio
    async def test_list_sprints_unauthorized_org(self, client: AsyncClient):
        """Test that listing sprints in unauthorized org fails."""
        unauthorized_org_id = uuid7()

        response = await client.get(f"/sprints?org_id={unauthorized_org_id}")
        assert response.status_code == 403


class TestGetSprint:
    """Test suite for GET /sprints/{sprint_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_sprint_success(
        self,
        client: AsyncClient,
        test_organization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a sprint."""
        sprint = KSprint(
            title="DevOps Sprint",
            status=SprintStatus.ACTIVE,
            end_ts=datetime(2024, 3, 31, 23, 59, 59),
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        response = await client.get(
            f"/sprints/{sprint.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sprint.id)
        assert data["title"] == "DevOps Sprint"
        assert data["status"] == "Active"

    @pytest.mark.asyncio
    async def test_get_sprint_not_found(self, client: AsyncClient, test_organization):
        """Test getting a non-existent sprint."""
        non_existent_id = uuid7()

        response = await client.get(
            f"/sprints/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_sprint_wrong_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a sprint with wrong org_id."""
        from app.models import KOrganization

        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        sprint = KSprint(
            title="Secret Sprint",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        # Try to access with unauthorized org
        wrong_org_id = uuid7()
        response = await client.get(f"/sprints/{sprint.id}?org_id={wrong_org_id}")
        assert response.status_code == 403


class TestUpdateSprint:
    """Test suite for PATCH /sprints/{sprint_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_sprint_success(
        self,
        client: AsyncClient,
        test_organization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully updating a sprint."""
        sprint = KSprint(
            title="Old Title",
            status=SprintStatus.BACKLOG,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        update_data = {
            "title": "New Title",
            "status": "Active",
            "end_ts": "2024-03-31T23:59:59",
            "meta": {"status": "updated"},
        }

        response = await client.patch(
            f"/sprints/{sprint.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["status"] == "Active"
        assert data["meta"] == {"status": "updated"}

    @pytest.mark.asyncio
    async def test_update_sprint_partial(
        self,
        client: AsyncClient,
        test_organization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a sprint."""
        sprint = KSprint(
            title="Original Sprint",
            status=SprintStatus.BACKLOG,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        update_data = {"status": "Active"}

        response = await client.patch(
            f"/sprints/{sprint.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Original Sprint"  # Unchanged
        assert data["status"] == "Active"  # Changed

    @pytest.mark.asyncio
    async def test_update_sprint_not_found(
        self, client: AsyncClient, test_organization
    ):
        """Test updating a non-existent sprint."""
        non_existent_id = uuid7()
        update_data = {"title": "New Title"}

        response = await client.patch(
            f"/sprints/{non_existent_id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_sprint_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a sprint in unauthorized org fails."""
        from app.models import KOrganization

        # Create a sprint in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        sprint = KSprint(
            title="Other Sprint",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        # Try to update with unauthorized org (user is not member of other_org)
        update_data = {"title": "Updated Title"}
        response = await client.patch(
            f"/sprints/{sprint.id}?org_id={other_org.id}",
            json=update_data,
        )
        assert response.status_code == 403


class TestDeleteSprint:
    """Test suite for DELETE /sprints/{sprint_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_sprint_success(
        self,
        client: AsyncClient,
        test_organization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting a sprint."""
        sprint = KSprint(
            title="To Delete",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        response = await client.delete(
            f"/sprints/{sprint.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204

        # Verify sprint is deleted
        get_response = await client.get(
            f"/sprints/{sprint.id}?org_id={test_organization.id}"
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_sprint_not_found(
        self, client: AsyncClient, test_organization
    ):
        """Test deleting a non-existent sprint."""
        non_existent_id = uuid7()

        response = await client.delete(
            f"/sprints/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_sprint_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a sprint in unauthorized org fails."""
        from app.models import KOrganization

        # Create a sprint in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        sprint = KSprint(
            title="Other Sprint",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        # Try to delete with unauthorized org (user is not member of other_org)
        response = await client.delete(f"/sprints/{sprint.id}?org_id={other_org.id}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_sprint_conflict(
        self,
        client: AsyncClient,
        test_organization,
        async_session: AsyncSession,
        test_user_id: UUID,
        mocker,
    ):
        """Test updating a sprint that causes a conflict."""
        from sqlalchemy.exc import IntegrityError

        sprint = KSprint(
            title="Test Sprint",
            status=SprintStatus.BACKLOG,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(sprint)
        await async_session.commit()
        await async_session.refresh(sprint)

        # Mock the commit to raise an IntegrityError
        mocker.patch.object(
            async_session,
            "commit",
            side_effect=IntegrityError(
                statement="UPDATE", params={}, orig=Exception("Constraint violation")
            ),
        )

        update_data = {"title": "Updated Title"}

        response = await client.patch(
            f"/sprints/{sprint.id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 409
        assert "Cannot update sprint" in response.json()["detail"]
