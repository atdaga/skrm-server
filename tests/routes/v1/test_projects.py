"""Unit tests for project management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KProject
from app.routes.deps import get_current_token
from app.routes.v1.projects import router
from app.schemas.user import TokenData
from tests.conftest import add_user_to_organization


@pytest.fixture
def app_with_overrides(
    async_session: AsyncSession, mock_token_data: TokenData
) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    async def override_get_db():
        yield async_session

    async def override_get_current_token():
        return mock_token_data

    from app.core.db.database import get_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_token] = override_get_current_token

    return app


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def test_organization(
    async_session: AsyncSession, test_user_id: UUID
) -> KOrganization:
    """Create a test organization with the test user as a member."""
    organization = KOrganization(
        name="Test Organization",
        alias="test_org",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(organization)
    await async_session.commit()
    await async_session.refresh(organization)

    # Add test user as organization principal
    await add_user_to_organization(async_session, organization.id, test_user_id)

    return organization


class TestCreateProject:
    """Test suite for POST /projects endpoint."""

    @pytest.mark.asyncio
    async def test_create_project_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
        test_scope: str,
    ):
        """Test successfully creating a new project."""
        project_data = {
            "name": "Mobile App Project",
            "description": "iOS and Android app development",
            "meta": {"priority": "high", "budget": 500000},
        }

        response = await client.post(
            f"/projects?org_id={test_organization.id}", json=project_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Mobile App Project"
        assert data["description"] == "iOS and Android app development"
        assert data["meta"] == {"priority": "high", "budget": 500000}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_create_project_minimal_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test creating a project with only required fields."""
        project_data = {"name": "Backend API"}

        response = await client.post(
            f"/projects?org_id={test_organization.id}", json=project_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Backend API"
        assert data["description"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_project_duplicate_name(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test that creating a project with duplicate name fails."""
        project_data = {"name": "Infrastructure Project"}

        # Create first project
        response = await client.post(
            f"/projects?org_id={test_organization.id}", json=project_data
        )
        assert response.status_code == 201

        # Try to create second project with same name
        response = await client.post(
            f"/projects?org_id={test_organization.id}", json=project_data
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_project_unauthorized_org(
        self, client: AsyncClient, test_user_id: UUID
    ):
        """Test that creating a project in unauthorized org fails."""
        unauthorized_org_id = uuid4()
        project_data = {"name": "Test Project"}

        response = await client.post(
            f"/projects?org_id={unauthorized_org_id}", json=project_data
        )
        assert response.status_code == 403


class TestListProjects:
    """Test suite for GET /projects endpoint."""

    @pytest.mark.asyncio
    async def test_list_projects_empty(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test listing projects when none exist."""
        response = await client.get(f"/projects?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []

    @pytest.mark.asyncio
    async def test_list_projects_multiple(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple projects."""
        # Create multiple projects
        projects = [
            KProject(
                name="Project Alpha",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
            KProject(
                name="Project Beta",
                description="Beta project",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
        ]

        for project in projects:
            async_session.add(project)
        await async_session.commit()

        response = await client.get(f"/projects?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 2
        project_names = [p["name"] for p in data["projects"]]
        assert "Project Alpha" in project_names
        assert "Project Beta" in project_names

    @pytest.mark.asyncio
    async def test_list_projects_unauthorized_org(self, client: AsyncClient):
        """Test that listing projects in unauthorized org fails."""
        unauthorized_org_id = uuid4()

        response = await client.get(f"/projects?org_id={unauthorized_org_id}")
        assert response.status_code == 403


class TestGetProject:
    """Test suite for GET /projects/{project_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_project_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a project."""
        project = KProject(
            name="DevOps Project",
            description="CI/CD pipeline setup",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        response = await client.get(
            f"/projects/{project.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project.id)
        assert data["name"] == "DevOps Project"
        assert data["description"] == "CI/CD pipeline setup"

    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test getting a non-existent project."""
        non_existent_id = uuid4()

        response = await client.get(
            f"/projects/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_wrong_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a project with wrong org_id."""
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        project = KProject(
            name="Secret Project",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        # Try to access with unauthorized org
        wrong_org_id = uuid4()
        response = await client.get(f"/projects/{project.id}?org_id={wrong_org_id}")
        assert response.status_code == 403


class TestUpdateProject:
    """Test suite for PATCH /projects/{project_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_project_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully updating a project."""
        project = KProject(
            name="Old Name",
            description="Old description",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        update_data = {
            "name": "New Name",
            "description": "New description",
            "meta": {"status": "updated"},
        }

        response = await client.patch(
            f"/projects/{project.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"
        assert data["meta"] == {"status": "updated"}

    @pytest.mark.asyncio
    async def test_update_project_partial(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a project."""
        project = KProject(
            name="Original Project",
            description="Original description",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        update_data = {"description": "Updated description"}

        response = await client.patch(
            f"/projects/{project.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original Project"  # Unchanged
        assert data["description"] == "Updated description"  # Changed

    @pytest.mark.asyncio
    async def test_update_project_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test updating a non-existent project."""
        non_existent_id = uuid4()
        update_data = {"name": "New Name"}

        response = await client.patch(
            f"/projects/{non_existent_id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project_duplicate_name(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating to a duplicate name fails."""
        project1 = KProject(
            name="Project One",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        project2 = KProject(
            name="Project Two",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )

        async_session.add_all([project1, project2])
        await async_session.commit()
        await async_session.refresh(project2)

        # Try to update project2 to have the same name as project1
        update_data = {"name": "Project One"}
        response = await client.patch(
            f"/projects/{project2.id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_project_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a project in unauthorized org fails."""
        # Create a project in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        project = KProject(
            name="Other Project",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        # Try to update with unauthorized org (user is not member of other_org)
        update_data = {"name": "Updated Name"}
        response = await client.patch(
            f"/projects/{project.id}?org_id={other_org.id}",
            json=update_data,
        )
        assert response.status_code == 403


class TestDeleteProject:
    """Test suite for DELETE /projects/{project_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_project_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting a project."""
        project = KProject(
            name="To Delete",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        response = await client.delete(
            f"/projects/{project.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204

        # Verify project is deleted
        get_response = await client.get(
            f"/projects/{project.id}?org_id={test_organization.id}"
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test deleting a non-existent project."""
        non_existent_id = uuid4()

        response = await client.delete(
            f"/projects/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a project in unauthorized org fails."""
        # Create a project in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        project = KProject(
            name="Other Project",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)

        # Try to delete with unauthorized org (user is not member of other_org)
        response = await client.delete(f"/projects/{project.id}?org_id={other_org.id}")
        assert response.status_code == 403
