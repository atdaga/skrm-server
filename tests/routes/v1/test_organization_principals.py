"""Unit tests for organization principal management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KOrganizationPrincipal, KPrincipal
from app.routes.deps import get_current_token
from app.routes.v1.organization_principals import router
from app.schemas.user import TokenData


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
async def organization(
    async_session: AsyncSession, test_user_id: UUID
) -> KOrganization:
    """Create a test organization."""
    organization = KOrganization(
        name="Test Organization",
        alias="test-org",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(organization)
    await async_session.commit()
    await async_session.refresh(organization)
    return organization


@pytest.fixture
async def principal(async_session: AsyncSession, test_user_id: UUID) -> KPrincipal:
    """Create a test principal."""
    principal = KPrincipal(
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
    await async_session.refresh(principal)
    return principal


class TestAddOrganizationPrincipal:
    """Test suite for POST /organizations/{org_id}/principals endpoint."""

    @pytest.mark.asyncio
    async def test_add_organization_principal_success(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        test_user_id: UUID,
    ):
        """Test successfully adding a new organization principal."""
        principal_data = {
            "principal_id": str(principal.id),
            "role": "admin",
            "meta": {"department": "Engineering", "level": "Senior"},
        }

        response = await client.post(
            f"/organizations/{organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["org_id"] == str(organization.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "admin"
        assert data["meta"] == {"department": "Engineering", "level": "Senior"}
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_add_organization_principal_minimal_data(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
    ):
        """Test adding an organization principal with minimal required fields."""
        principal_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/organizations/{organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["org_id"] == str(organization.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_organization_principal_duplicate(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that adding a duplicate organization principal fails."""
        # Add principal directly in database
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()
        async_session.expunge(org_principal)

        # Try to add same principal via API
        principal_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/organizations/{organization.id}/principals", json=principal_data
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_organization_principal_org_not_found(
        self,
        client: AsyncClient,
        principal: KPrincipal,
    ):
        """Test adding a principal to a non-existent organization."""
        non_existent_org_id = uuid4()
        principal_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/organizations/{non_existent_org_id}/principals", json=principal_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_organization_principal_with_role(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
    ):
        """Test adding an organization principal with a specific role."""
        principal_data = {"principal_id": str(principal.id), "role": "manager"}

        response = await client.post(
            f"/organizations/{organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "manager"

    @pytest.mark.asyncio
    async def test_add_organization_principal_with_complex_meta(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
    ):
        """Test adding an organization principal with complex metadata."""
        principal_data = {
            "principal_id": str(principal.id),
            "role": "engineer",
            "meta": {
                "skills": ["Python", "FastAPI", "SQLAlchemy"],
                "certifications": {"aws": True, "gcp": False},
                "performance": {"rating": 4.5, "reviews": 12},
            },
        }

        response = await client.post(
            f"/organizations/{organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == principal_data["meta"]


class TestListOrganizationPrincipals:
    """Test suite for GET /organizations/{org_id}/principals endpoint."""

    @pytest.mark.asyncio
    async def test_list_organization_principals_empty(
        self,
        client: AsyncClient,
        organization: KOrganization,
    ):
        """Test listing organization principals when none exist."""
        response = await client.get(f"/organizations/{organization.id}/principals")

        assert response.status_code == 200
        data = response.json()
        assert data["principals"] == []

    @pytest.mark.asyncio
    async def test_list_organization_principals_single(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing organization principals with a single principal."""
        # Add a principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="admin",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        response = await client.get(f"/organizations/{organization.id}/principals")

        assert response.status_code == 200
        data = response.json()
        assert len(data["principals"]) == 1
        assert data["principals"][0]["org_id"] == str(organization.id)
        assert data["principals"][0]["principal_id"] == str(principal.id)
        assert data["principals"][0]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_list_organization_principals_multiple(
        self,
        client: AsyncClient,
        organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple organization principals."""
        # Create multiple principals and add them
        principals_data = [
            {"username": "user1", "email": "user1@example.com", "role": "admin"},
            {"username": "user2", "email": "user2@example.com", "role": "engineer"},
            {"username": "user3", "email": "user3@example.com", "role": "manager"},
        ]

        for idx, p_data in enumerate(principals_data):
            principal = KPrincipal(
                username=p_data["username"],
                primary_email=p_data["email"],
                first_name="User",
                last_name=str(idx),
                display_name=f"User {idx}",
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(principal)
            await async_session.commit()
            await async_session.refresh(principal)

            org_principal = KOrganizationPrincipal(
                org_id=organization.id,
                principal_id=principal.id,
                role=p_data["role"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(org_principal)

        await async_session.commit()

        response = await client.get(f"/organizations/{organization.id}/principals")

        assert response.status_code == 200
        data = response.json()
        assert len(data["principals"]) == 3
        roles = {p["role"] for p in data["principals"]}
        assert roles == {"admin", "engineer", "manager"}

    @pytest.mark.asyncio
    async def test_list_organization_principals_org_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing principals of a non-existent organization."""
        non_existent_org_id = uuid4()

        response = await client.get(f"/organizations/{non_existent_org_id}/principals")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetOrganizationPrincipal:
    """Test suite for GET /organizations/{org_id}/principals/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_organization_principal_success(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully getting a single organization principal."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="admin",
            meta={"level": "senior"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        response = await client.get(
            f"/organizations/{organization.id}/principals/{principal.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["org_id"] == str(organization.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "admin"
        assert data["meta"] == {"level": "senior"}

    @pytest.mark.asyncio
    async def test_get_organization_principal_not_found(
        self,
        client: AsyncClient,
        organization: KOrganization,
    ):
        """Test getting an organization principal that doesn't exist."""
        non_existent_principal_id = uuid4()

        response = await client.get(
            f"/organizations/{organization.id}/principals/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateOrganizationPrincipal:
    """Test suite for PATCH /organizations/{org_id}/principals/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_organization_principal_role(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating an organization principal's role."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="member",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {"role": "admin"}

        response = await client.patch(
            f"/organizations/{organization.id}/principals/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["org_id"] == str(organization.id)
        assert data["principal_id"] == str(principal.id)

    @pytest.mark.asyncio
    async def test_update_organization_principal_meta(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating an organization principal's metadata."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {"meta": {"new": "data", "updated": True}}

        response = await client.patch(
            f"/organizations/{organization.id}/principals/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}

    @pytest.mark.asyncio
    async def test_update_organization_principal_both_fields(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating both role and meta."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="member",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {"role": "senior_member", "meta": {"new": "data"}}

        response = await client.patch(
            f"/organizations/{organization.id}/principals/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "senior_member"
        assert data["meta"] == {"new": "data"}

    @pytest.mark.asyncio
    async def test_update_organization_principal_not_found(
        self,
        client: AsyncClient,
        organization: KOrganization,
    ):
        """Test updating an organization principal that doesn't exist."""
        non_existent_principal_id = uuid4()
        update_data = {"role": "admin"}

        response = await client.patch(
            f"/organizations/{organization.id}/principals/{non_existent_principal_id}",
            json=update_data,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_organization_principal_empty_payload(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="member",
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {}

        response = await client.patch(
            f"/organizations/{organization.id}/principals/{principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "member"
        assert data["meta"] == {"key": "value"}


class TestRemoveOrganizationPrincipal:
    """Test suite for DELETE /organizations/{org_id}/principals/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_organization_principal_success(
        self,
        client: AsyncClient,
        organization: KOrganization,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully removing an organization principal."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        response = await client.delete(
            f"/organizations/{organization.id}/principals/{principal.id}"
        )

        assert response.status_code == 204
        assert response.content == b""

        # Verify principal is actually deleted
        from sqlmodel import select

        result = await async_session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == organization.id,
                KOrganizationPrincipal.principal_id == principal.id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_organization_principal_not_found(
        self,
        client: AsyncClient,
        organization: KOrganization,
    ):
        """Test removing an organization principal that doesn't exist."""
        non_existent_principal_id = uuid4()

        response = await client.delete(
            f"/organizations/{organization.id}/principals/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
