"""Unit tests for deployment environment management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KDeploymentEnv, KOrganization
from app.routes.deps import get_current_token
from app.routes.v1.deployment_envs import router
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
    from app.models import KPrincipal

    # Create a principal for the test user
    principal = KPrincipal(
        id=test_user_id,
        username="testuser",
        primary_email="test@example.com",
        first_name="Test",
        last_name="User",
        display_name="Test User",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()

    organization = KOrganization(
        name="Test Organization",
        alias="test_org",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(organization)
    await async_session.commit()
    await async_session.refresh(organization)

    # Add user to organization
    await add_user_to_organization(async_session, organization.id, test_user_id)

    return organization


class TestCreateDeploymentEnv:
    """Test suite for POST /deployment-envs endpoint."""

    @pytest.mark.asyncio
    async def test_create_deployment_env_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
        test_scope: str,
    ):
        """Test successfully creating a new deployment environment."""
        deployment_env_data = {
            "name": "Production",
            "meta": {"region": "us-east-1", "replicas": 3},
        }

        response = await client.post(
            f"/deployment-envs?org_id={test_organization.id}", json=deployment_env_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Production"
        assert data["meta"] == {"region": "us-east-1", "replicas": 3}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_create_deployment_env_minimal_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test creating a deployment environment with only required fields."""
        deployment_env_data = {"name": "Staging"}

        response = await client.post(
            f"/deployment-envs?org_id={test_organization.id}", json=deployment_env_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Staging"
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_deployment_env_duplicate_name(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test that creating a deployment environment with duplicate name fails."""
        deployment_env_data = {"name": "Development"}

        # Create first deployment environment
        response = await client.post(
            f"/deployment-envs?org_id={test_organization.id}", json=deployment_env_data
        )
        assert response.status_code == 201

        # Try to create second deployment environment with same name
        response = await client.post(
            f"/deployment-envs?org_id={test_organization.id}", json=deployment_env_data
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_deployment_env_unauthorized_org(
        self, client: AsyncClient, test_user_id: UUID
    ):
        """Test that creating a deployment environment in unauthorized org fails."""
        unauthorized_org_id = uuid4()
        deployment_env_data = {"name": "Test Env"}

        response = await client.post(
            f"/deployment-envs?org_id={unauthorized_org_id}", json=deployment_env_data
        )
        assert response.status_code == 403


class TestListDeploymentEnvs:
    """Test suite for GET /deployment-envs endpoint."""

    @pytest.mark.asyncio
    async def test_list_deployment_envs_empty(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test listing deployment environments when none exist."""
        response = await client.get(f"/deployment-envs?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deployment_envs"] == []

    @pytest.mark.asyncio
    async def test_list_deployment_envs_multiple(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple deployment environments."""
        # Create multiple deployment environments
        deployment_envs = [
            KDeploymentEnv(
                name="Production",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
            KDeploymentEnv(
                name="Staging",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
        ]

        for deployment_env in deployment_envs:
            async_session.add(deployment_env)
        await async_session.commit()

        response = await client.get(f"/deployment-envs?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["deployment_envs"]) == 2
        env_names = [e["name"] for e in data["deployment_envs"]]
        assert "Production" in env_names
        assert "Staging" in env_names

    @pytest.mark.asyncio
    async def test_list_deployment_envs_unauthorized_org(self, client: AsyncClient):
        """Test that listing deployment environments in unauthorized org fails."""
        unauthorized_org_id = uuid4()

        response = await client.get(f"/deployment-envs?org_id={unauthorized_org_id}")
        assert response.status_code == 403


class TestGetDeploymentEnv:
    """Test suite for GET /deployment-envs/{deployment_env_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_deployment_env_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a deployment environment."""
        deployment_env = KDeploymentEnv(
            name="QA",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        response = await client.get(
            f"/deployment-envs/{deployment_env.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(deployment_env.id)
        assert data["name"] == "QA"

    @pytest.mark.asyncio
    async def test_get_deployment_env_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test getting a non-existent deployment environment."""
        non_existent_id = uuid4()

        response = await client.get(
            f"/deployment-envs/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_deployment_env_wrong_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a deployment environment with wrong org_id."""
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        deployment_env = KDeploymentEnv(
            name="Secret Env",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        # Try to access with unauthorized org
        wrong_org_id = uuid4()
        response = await client.get(
            f"/deployment-envs/{deployment_env.id}?org_id={wrong_org_id}"
        )
        assert response.status_code == 403


class TestUpdateDeploymentEnv:
    """Test suite for PATCH /deployment-envs/{deployment_env_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_deployment_env_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully updating a deployment environment."""
        deployment_env = KDeploymentEnv(
            name="Old Name",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        update_data = {
            "name": "New Name",
            "meta": {"region": "us-west-2"},
        }

        response = await client.patch(
            f"/deployment-envs/{deployment_env.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["meta"] == {"region": "us-west-2"}

    @pytest.mark.asyncio
    async def test_update_deployment_env_partial(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a deployment environment."""
        deployment_env = KDeploymentEnv(
            name="Original Env",
            meta={"key": "value"},
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        update_data = {"meta": {"key": "new_value"}}

        response = await client.patch(
            f"/deployment-envs/{deployment_env.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original Env"  # Unchanged
        assert data["meta"] == {"key": "new_value"}  # Changed

    @pytest.mark.asyncio
    async def test_update_deployment_env_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test updating a non-existent deployment environment."""
        non_existent_id = uuid4()
        update_data = {"name": "New Name"}

        response = await client.patch(
            f"/deployment-envs/{non_existent_id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_deployment_env_duplicate_name(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating to a duplicate name fails."""
        deployment_env1 = KDeploymentEnv(
            name="Env One",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        deployment_env2 = KDeploymentEnv(
            name="Env Two",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )

        async_session.add_all([deployment_env1, deployment_env2])
        await async_session.commit()
        await async_session.refresh(deployment_env2)

        # Try to update deployment_env2 to have the same name as deployment_env1
        update_data = {"name": "Env One"}
        response = await client.patch(
            f"/deployment-envs/{deployment_env2.id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_deployment_env_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a deployment environment in unauthorized org fails."""
        # Create a deployment environment in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        deployment_env = KDeploymentEnv(
            name="Other Env",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        # Try to update with unauthorized org (user is not member of other_org)
        update_data = {"name": "Updated Name"}
        response = await client.patch(
            f"/deployment-envs/{deployment_env.id}?org_id={other_org.id}",
            json=update_data,
        )
        assert response.status_code == 403


class TestDeleteDeploymentEnv:
    """Test suite for DELETE /deployment-envs/{deployment_env_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_deployment_env_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting a deployment environment."""
        deployment_env = KDeploymentEnv(
            name="To Delete",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        response = await client.delete(
            f"/deployment-envs/{deployment_env.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204

        # Verify deployment environment is deleted
        get_response = await client.get(
            f"/deployment-envs/{deployment_env.id}?org_id={test_organization.id}"
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_deployment_env_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test deleting a non-existent deployment environment."""
        non_existent_id = uuid4()

        response = await client.delete(
            f"/deployment-envs/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_deployment_env_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a deployment environment in unauthorized org fails."""
        # Create a deployment environment in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        deployment_env = KDeploymentEnv(
            name="Other Env",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(deployment_env)
        await async_session.commit()
        await async_session.refresh(deployment_env)

        # Try to delete with unauthorized org (user is not member of other_org)
        response = await client.delete(
            f"/deployment-envs/{deployment_env.id}?org_id={other_org.id}"
        )
        assert response.status_code == 403
