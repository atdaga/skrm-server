"""Unit tests for organization principal management endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KOrganizationPrincipal, KPrincipal
from app.routes.v1.organization_principals import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with organization principals router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestAddOrganizationPrincipal:
    """Test suite for POST /organizations/{org_id}/principals endpoint."""

    @pytest.mark.asyncio
    async def test_add_organization_principal_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        test_user_id: UUID,
    ):
        """Test successfully adding a new organization principal."""
        principal_data = {
            "principal_id": str(test_principal.id),
            "role": "admin",
            "meta": {"department": "Engineering", "level": "Senior"},
        }

        response = await client.post(
            f"/organizations/{test_organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["org_id"] == str(test_organization.id)
        assert data["principal_id"] == str(test_principal.id)
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
        test_organization: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test adding an organization principal with minimal required fields."""
        principal_data = {"principal_id": str(test_principal.id)}

        response = await client.post(
            f"/organizations/{test_organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["org_id"] == str(test_organization.id)
        assert data["principal_id"] == str(test_principal.id)
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_organization_principal_duplicate(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that adding a duplicate organization principal fails."""
        # Note: test_user_id principal already exists from test_organization fixture
        # Add principal directly in database
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()
        async_session.expunge(org_principal)

        # Try to add same principal via API
        principal_data = {"principal_id": str(test_principal.id)}

        response = await client.post(
            f"/organizations/{test_organization.id}/principals", json=principal_data
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_organization_principal_org_not_found(
        self,
        client: AsyncClient,
        test_principal: KPrincipal,
    ):
        """Test adding a principal to a non-existent organization."""
        non_existent_org_id = uuid4()
        principal_data = {"principal_id": str(test_principal.id)}

        response = await client.post(
            f"/organizations/{non_existent_org_id}/principals", json=principal_data
        )

        # Returns 403 because user is not a member of non-existent org
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_add_organization_principal_with_role(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test adding an organization principal with a specific role."""
        principal_data = {"principal_id": str(test_principal.id), "role": "manager"}

        response = await client.post(
            f"/organizations/{test_organization.id}/principals", json=principal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "manager"

    @pytest.mark.asyncio
    async def test_add_organization_principal_with_complex_meta(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test adding an organization principal with complex metadata."""
        principal_data = {
            "principal_id": str(test_principal.id),
            "role": "engineer",
            "meta": {
                "skills": ["Python", "FastAPI", "SQLAlchemy"],
                "certifications": {"aws": True, "gcp": False},
                "performance": {"rating": 4.5, "reviews": 12},
            },
        }

        response = await client.post(
            f"/organizations/{test_organization.id}/principals", json=principal_data
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
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test listing organization principals when only the test user exists."""
        response = await client.get(f"/organizations/{test_organization.id}/principals")

        assert response.status_code == 200
        data = response.json()
        # Should have 1 principal - the test user added by the fixture
        assert len(data["principals"]) == 1
        assert data["principals"][0]["principal_id"] == str(test_user_id)

    @pytest.mark.asyncio
    async def test_list_organization_principals_single(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing organization principals with a single additional principal."""
        # Add a principal (in addition to test user from fixture)
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="admin",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        response = await client.get(f"/organizations/{test_organization.id}/principals")

        assert response.status_code == 200
        data = response.json()
        # Should have 2 principals - test user from fixture + the one we just added
        assert len(data["principals"]) == 2
        principal_ids = {p["principal_id"] for p in data["principals"]}
        assert str(test_principal.id) in principal_ids
        assert str(test_user_id) in principal_ids

    @pytest.mark.asyncio
    async def test_list_organization_principals_multiple(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
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
                org_id=test_organization.id,
                principal_id=principal.id,
                role=p_data["role"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(org_principal)

        await async_session.commit()

        response = await client.get(f"/organizations/{test_organization.id}/principals")

        assert response.status_code == 200
        data = response.json()
        # Should have 4 principals - test user from fixture + 3 we just added
        assert len(data["principals"]) == 4
        # Filter out the test user (which has no role) to check the roles we added
        principals_with_role = [p for p in data["principals"] if p["role"] is not None]
        roles = {p["role"] for p in principals_with_role}
        assert roles == {"admin", "engineer", "manager"}

    @pytest.mark.asyncio
    async def test_list_organization_principals_org_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing principals of a non-existent organization."""
        non_existent_org_id = uuid4()

        response = await client.get(f"/organizations/{non_existent_org_id}/principals")

        # Returns 403 because user is not a member of non-existent org
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()


class TestGetOrganizationPrincipal:
    """Test suite for GET /organizations/{org_id}/principals/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_organization_principal_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully getting a single organization principal."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="admin",
            meta={"level": "senior"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        response = await client.get(
            f"/organizations/{test_organization.id}/principals/{test_principal.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["org_id"] == str(test_organization.id)
        assert data["principal_id"] == str(test_principal.id)
        assert data["role"] == "admin"
        assert data["meta"] == {"level": "senior"}

    @pytest.mark.asyncio
    async def test_get_organization_principal_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test getting an organization principal that doesn't exist."""
        non_existent_principal_id = uuid4()

        response = await client.get(
            f"/organizations/{test_organization.id}/principals/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateOrganizationPrincipal:
    """Test suite for PATCH /organizations/{org_id}/principals/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_organization_principal_role(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating an organization principal's role."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="member",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {"role": "admin"}

        response = await client.patch(
            f"/organizations/{test_organization.id}/principals/{test_principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["org_id"] == str(test_organization.id)
        assert data["principal_id"] == str(test_principal.id)

    @pytest.mark.asyncio
    async def test_update_organization_principal_meta(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating an organization principal's metadata."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {"meta": {"new": "data", "updated": True}}

        response = await client.patch(
            f"/organizations/{test_organization.id}/principals/{test_principal.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}

    @pytest.mark.asyncio
    async def test_update_organization_principal_both_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating both role and meta."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="member",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {"role": "senior_member", "meta": {"new": "data"}}

        response = await client.patch(
            f"/organizations/{test_organization.id}/principals/{test_principal.id}",
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
        test_organization: KOrganization,
    ):
        """Test updating an organization principal that doesn't exist."""
        non_existent_principal_id = uuid4()
        update_data = {"role": "admin"}

        response = await client.patch(
            f"/organizations/{test_organization.id}/principals/{non_existent_principal_id}",
            json=update_data,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_organization_principal_empty_payload(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="member",
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        update_data = {}

        response = await client.patch(
            f"/organizations/{test_organization.id}/principals/{test_principal.id}",
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
        test_organization: KOrganization,
        test_principal: KPrincipal,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully removing an organization principal."""
        # Add principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org_principal)
        await async_session.commit()

        response = await client.delete(
            f"/organizations/{test_organization.id}/principals/{test_principal.id}"
        )

        assert response.status_code == 204
        assert response.content == b""

        # Verify principal is actually deleted
        from sqlmodel import select

        result = await async_session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == test_organization.id,
                KOrganizationPrincipal.principal_id == test_principal.id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_organization_principal_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test removing an organization principal that doesn't exist."""
        non_existent_principal_id = uuid4()

        response = await client.delete(
            f"/organizations/{test_organization.id}/principals/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUnauthorizedOrganizationPrincipalAccess:
    """Test suite for unauthorized organization principal access scenarios."""

    @pytest.mark.asyncio
    async def test_add_principal_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test adding a principal to an organization user is not a member of."""
        principal_data = {"principal_id": str(test_principal.id)}
        response = await client.post(
            f"/organizations/{test_organization_without_membership.id}/principals",
            json=principal_data,
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_principals_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
    ):
        """Test listing principals of an organization user is not a member of."""
        response = await client.get(
            f"/organizations/{test_organization_without_membership.id}/principals"
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_principal_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test getting a principal from an organization user is not a member of."""
        response = await client.get(
            f"/organizations/{test_organization_without_membership.id}/principals/{test_principal.id}"
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_principal_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test updating a principal in an organization user is not a member of."""
        update_data = {"role": "admin"}
        response = await client.patch(
            f"/organizations/{test_organization_without_membership.id}/principals/{test_principal.id}",
            json=update_data,
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_remove_principal_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test removing a principal from an organization user is not a member of."""
        response = await client.delete(
            f"/organizations/{test_organization_without_membership.id}/principals/{test_principal.id}"
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()


class TestOrganizationPrincipalDataInconsistency:
    """Test suite for data inconsistency scenarios (membership exists but org doesn't)."""

    @pytest.mark.asyncio
    async def test_add_principal_org_not_found(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_principal: KPrincipal,
        test_user_id: UUID,
    ):
        """Test adding a principal when user is member but org doesn't exist."""
        # test_principal fixture already creates the test_user_id principal if needed
        # Just create a fake org_id and add user as member WITHOUT creating the org
        # Use raw SQL to bypass foreign key constraint
        from datetime import datetime

        from sqlalchemy import text

        fake_org_id = uuid4()
        await async_session.execute(text("PRAGMA foreign_keys = OFF"))
        await async_session.execute(
            text(
                "INSERT INTO k_organization_principal "
                "(org_id, principal_id, role, meta, created, created_by, last_modified, last_modified_by) "
                "VALUES (:org_id, :principal_id, NULL, '{}', :created, :created_by, :last_modified, :last_modified_by)"
            ),
            {
                "org_id": str(fake_org_id).replace("-", ""),
                "principal_id": str(test_user_id).replace("-", ""),
                "created": datetime.now(),
                "created_by": str(test_user_id).replace("-", ""),
                "last_modified": datetime.now(),
                "last_modified_by": str(test_user_id).replace("-", ""),
            },
        )
        await async_session.commit()
        await async_session.execute(text("PRAGMA foreign_keys = ON"))
        await async_session.commit()

        principal_data = {"principal_id": str(test_principal.id)}
        response = await client.post(
            f"/organizations/{fake_org_id}/principals", json=principal_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_principals_org_not_found(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing principals when user is member but org doesn't exist."""
        # Create principal first
        from datetime import datetime

        from sqlalchemy import text

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

        # Create a fake org_id and add user as member WITHOUT creating the org
        # Use raw SQL to bypass foreign key constraint
        fake_org_id = uuid4()
        await async_session.execute(text("PRAGMA foreign_keys = OFF"))
        await async_session.execute(
            text(
                "INSERT INTO k_organization_principal "
                "(org_id, principal_id, role, meta, created, created_by, last_modified, last_modified_by) "
                "VALUES (:org_id, :principal_id, NULL, '{}', :created, :created_by, :last_modified, :last_modified_by)"
            ),
            {
                "org_id": str(fake_org_id).replace("-", ""),
                "principal_id": str(test_user_id).replace("-", ""),
                "created": datetime.now(),
                "created_by": str(test_user_id).replace("-", ""),
                "last_modified": datetime.now(),
                "last_modified_by": str(test_user_id).replace("-", ""),
            },
        )
        await async_session.commit()
        await async_session.execute(text("PRAGMA foreign_keys = ON"))
        await async_session.commit()

        response = await client.get(f"/organizations/{fake_org_id}/principals")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
