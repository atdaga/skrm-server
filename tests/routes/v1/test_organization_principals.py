"""Unit tests for organization principal management endpoints."""

from uuid import UUID, uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KOrganizationPrincipal, KPrincipal
from app.routes.v1.organization_principals import router
from app.schemas.user import UserDetail


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with organization principals router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestAddOrganizationPrincipal:
    """Test suite for POST /organizations/{org_id}/principals endpoint."""

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

    async def test_add_organization_principal_org_not_found(
        self,
        client: AsyncClient,
        test_principal: KPrincipal,
    ):
        """Test adding a principal to a non-existent organization."""
        non_existent_org_id = uuid7()
        principal_data = {"principal_id": str(test_principal.id)}

        response = await client.post(
            f"/organizations/{non_existent_org_id}/principals", json=principal_data
        )

        # Returns 404 because organization doesn't exist
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

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

    async def test_add_organization_principal_unauthorized_access(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
    ):
        """Test adding a principal when user is not authorized to access the organization."""
        from unittest.mock import AsyncMock, patch

        from app.core.exceptions.domain_exceptions import (
            UnauthorizedOrganizationAccessException,
        )

        principal_data = {"principal_id": str(test_principal.id)}

        # Mock the logic function to raise UnauthorizedOrganizationAccessException
        with patch(
            "app.routes.v1.organization_principals.organization_principals_logic.add_organization_principal",
            new_callable=AsyncMock,
        ) as mock_add:
            mock_add.side_effect = UnauthorizedOrganizationAccessException(
                org_id=test_organization.id, user_id=test_principal.id
            )

            response = await client.post(
                f"/organizations/{test_organization.id}/principals", json=principal_data
            )

            assert response.status_code == 403
            assert "not authorized" in response.json()["detail"].lower()


class TestListOrganizationPrincipals:
    """Test suite for GET /organizations/{org_id}/principals endpoint."""

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

    async def test_list_organization_principals_org_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing principals of a non-existent organization."""
        non_existent_org_id = uuid7()

        response = await client.get(f"/organizations/{non_existent_org_id}/principals")

        # Returns 403 because user is not a member of non-existent org
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()


class TestGetOrganizationPrincipal:
    """Test suite for GET /organizations/{org_id}/principals/{principal_id} endpoint."""

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

    async def test_get_organization_principal_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test getting an organization principal that doesn't exist."""
        non_existent_principal_id = uuid7()

        response = await client.get(
            f"/organizations/{test_organization.id}/principals/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateOrganizationPrincipal:
    """Test suite for PATCH /organizations/{org_id}/principals/{principal_id} endpoint."""

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

    async def test_update_organization_principal_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test updating an organization principal that doesn't exist."""
        non_existent_principal_id = uuid7()
        update_data = {"role": "admin"}

        response = await client.patch(
            f"/organizations/{test_organization.id}/principals/{non_existent_principal_id}",
            json=update_data,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

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

        # Verify principal is soft-deleted
        from sqlmodel import select

        result = await async_session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == test_organization.id,
                KOrganizationPrincipal.principal_id == test_principal.id,
            )
        )
        deleted_org_principal = result.scalar_one_or_none()
        assert deleted_org_principal is not None
        assert deleted_org_principal.deleted_at is not None

    async def test_remove_organization_principal_not_found(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test removing an organization principal that doesn't exist."""
        non_existent_principal_id = uuid7()

        response = await client.delete(
            f"/organizations/{test_organization.id}/principals/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUnauthorizedOrganizationPrincipalAccess:
    """Test suite for unauthorized organization principal access scenarios."""

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


class TestOrganizationPrincipalDataInconsistency:
    """Test suite for data inconsistency scenarios (membership exists but org doesn't)."""

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

        fake_org_id = uuid7()
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
        fake_org_id = uuid7()
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


class TestSystemRoleAuthorization:
    """Test suite for system role authorization on CUD operations."""

    async def test_add_principal_without_system_role(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        mock_client_user: UserDetail,
        async_session: AsyncSession,
    ):
        """Test adding a principal without proper system role."""
        from app.core.db.database import get_db
        from app.routes.deps import get_current_user

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_client_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            principal_data = {"principal_id": str(test_principal.id)}
            response = await test_client.post(
                f"/organizations/{test_organization.id}/principals",
                json=principal_data,
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()

    async def test_update_principal_without_system_role(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        mock_client_user: UserDetail,
        mock_user_detail: UserDetail,
        async_session: AsyncSession,
    ):
        """Test updating a principal without proper system role."""
        from app.core.db.database import get_db
        from app.routes.deps import get_current_user

        # First create an organization principal with admin user
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="member",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(org_principal)
        await async_session.commit()
        await async_session.refresh(org_principal)

        # Now try to update with client user
        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_client_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            update_data = {"role": "admin"}
            response = await test_client.patch(
                f"/organizations/{org_principal.org_id}/principals/{org_principal.principal_id}",
                json=update_data,
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()

    async def test_remove_principal_without_system_role(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        mock_client_user: UserDetail,
        mock_user_detail: UserDetail,
        async_session: AsyncSession,
    ):
        """Test removing a principal without proper system role."""
        from app.core.db.database import get_db
        from app.routes.deps import get_current_user

        # First create an organization principal with admin user
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="member",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(org_principal)
        await async_session.commit()
        await async_session.refresh(org_principal)

        # Now try to remove with client user
        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_client_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            response = await test_client.delete(
                f"/organizations/{org_principal.org_id}/principals/{org_principal.principal_id}"
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()

    async def test_remove_principal_hard_delete_without_privileges(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_principal: KPrincipal,
        mock_user_detail: UserDetail,
        async_session: AsyncSession,
    ):
        """Test hard delete requires SYSTEM or SYSTEM_ROOT role (not SYSTEM_ADMIN)."""
        from app.core.db.database import get_db
        from app.models.k_principal import SystemRole
        from app.routes.deps import get_current_user
        from app.schemas.user import UserDetail as UD

        # First create an organization principal
        org_principal = KOrganizationPrincipal(
            org_id=test_organization.id,
            principal_id=test_principal.id,
            role="member",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(org_principal)
        await async_session.commit()
        await async_session.refresh(org_principal)

        # Create a user with SYSTEM_ADMIN role (not allowed for hard delete)
        system_admin_user = UD(
            id=mock_user_detail.id,
            username=mock_user_detail.username,
            primary_email=mock_user_detail.primary_email,
            primary_email_verified=mock_user_detail.primary_email_verified,
            primary_phone=mock_user_detail.primary_phone,
            primary_phone_verified=mock_user_detail.primary_phone_verified,
            enabled=mock_user_detail.enabled,
            time_zone=mock_user_detail.time_zone,
            name_prefix=mock_user_detail.name_prefix,
            first_name=mock_user_detail.first_name,
            middle_name=mock_user_detail.middle_name,
            last_name=mock_user_detail.last_name,
            name_suffix=mock_user_detail.name_suffix,
            display_name=mock_user_detail.display_name,
            default_locale=mock_user_detail.default_locale,
            scope=mock_user_detail.scope,
            system_role=SystemRole.SYSTEM_ADMIN,  # This role can't hard delete
            meta=mock_user_detail.meta,
            deleted_at=mock_user_detail.deleted_at,
            created=mock_user_detail.created,
            created_by=mock_user_detail.created_by,
            last_modified=mock_user_detail.last_modified,
            last_modified_by=mock_user_detail.last_modified_by,
        )

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return system_admin_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            response = await test_client.delete(
                f"/organizations/{org_principal.org_id}/principals/{org_principal.principal_id}?hard_delete=true"
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()
