"""Unit tests for organization management endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KOrganization, KOrganizationPrincipal
from app.routes.v1.organizations import router
from tests.conftest import add_user_to_organization


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with organization router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestCreateOrganization:
    """Test suite for POST /organizations endpoint."""

    @pytest.mark.asyncio
    async def test_create_organization_success(
        self,
        client: AsyncClient,
        test_user_id: UUID,
    ):
        """Test successfully creating a new organization."""
        org_data = {
            "name": "Acme Corporation",
            "alias": "acme_corp",
            "meta": {"industry": "Technology", "location": "SF"},
        }

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Corporation"
        assert data["alias"] == "acme_corp"
        assert data["meta"] == {"industry": "Technology", "location": "SF"}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_create_organization_minimal_data(
        self,
        client: AsyncClient,
    ):
        """Test creating an organization with minimal required fields."""
        org_data = {"name": "Minimal Org", "alias": "minimal_org"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Org"
        assert data["alias"] == "minimal_org"
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that creating an organization with duplicate name fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create first organization
        org = KOrganization(
            name="Duplicate Org",
            alias="duplicate_org_1",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()

        # Try to create another organization with same name
        org_data = {"name": "Duplicate Org", "alias": "duplicate_org_2"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_alias(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that creating an organization with duplicate alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create first organization
        org = KOrganization(
            name="First Org",
            alias="same_alias",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()

        # Try to create another organization with same alias
        org_data = {"name": "Second Org", "alias": "same_alias"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_organization_invalid_alias_empty(
        self,
        client: AsyncClient,
    ):
        """Test that empty alias is rejected."""
        org_data = {"name": "Invalid Org", "alias": ""}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alias" in str(error).lower() for error in detail)

    @pytest.mark.asyncio
    async def test_create_organization_invalid_alias_uppercase(
        self,
        client: AsyncClient,
    ):
        """Test that uppercase letters in alias are rejected."""
        org_data = {"name": "Invalid Org", "alias": "Invalid_Alias"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alias" in str(error).lower() for error in detail)

    @pytest.mark.asyncio
    async def test_create_organization_invalid_alias_mixed_case(
        self,
        client: AsyncClient,
    ):
        """Test that mixed case alias is rejected."""
        # Use alias that starts with lowercase and has valid chars but contains uppercase
        # This specifically tests the final islower() check
        org_data = {"name": "Invalid Org", "alias": "mixed_Case"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alias" in str(error).lower() for error in detail)

    @pytest.mark.asyncio
    async def test_create_organization_invalid_alias_all_uppercase(
        self,
        client: AsyncClient,
    ):
        """Test that all uppercase alias is rejected."""
        org_data = {"name": "Invalid Org", "alias": "ABC"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alias" in str(error).lower() for error in detail)

    @pytest.mark.asyncio
    async def test_create_organization_invalid_alias_starts_with_digit(
        self,
        client: AsyncClient,
    ):
        """Test that alias starting with digit is rejected."""
        org_data = {"name": "Invalid Org", "alias": "123_org"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alias" in str(error).lower() for error in detail)

    @pytest.mark.asyncio
    async def test_create_organization_invalid_alias_special_chars(
        self,
        client: AsyncClient,
    ):
        """Test that special characters in alias are rejected."""
        org_data = {"name": "Invalid Org", "alias": "org-name"}

        response = await client.post("/organizations", json=org_data)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("alias" in str(error).lower() for error in detail)

    @pytest.mark.asyncio
    async def test_create_organization_valid_aliases(
        self,
        client: AsyncClient,
    ):
        """Test various valid alias formats."""
        valid_aliases = [
            ("Org 1", "acme"),
            ("Org 2", "acme_corp"),
            ("Org 3", "org123"),
            ("Org 4", "my_org_2"),
        ]

        for name, alias in valid_aliases:
            org_data = {"name": name, "alias": alias}
            response = await client.post("/organizations", json=org_data)
            assert response.status_code == 201
            data = response.json()
            assert data["alias"] == alias


class TestListOrganizations:
    """Test suite for GET /organizations endpoint."""

    @pytest.mark.asyncio
    async def test_list_organizations_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing organizations when none exist."""
        response = await client.get("/organizations")

        assert response.status_code == 200
        data = response.json()
        assert data["organizations"] == []

    @pytest.mark.asyncio
    async def test_list_organizations_single(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test listing organizations with a single organization."""
        response = await client.get("/organizations")

        assert response.status_code == 200
        data = response.json()
        assert len(data["organizations"]) == 1
        assert data["organizations"][0]["name"] == "Test Organization"
        assert data["organizations"][0]["alias"] == "test_org"
        assert data["organizations"][0]["id"] == str(test_organization.id)

    @pytest.mark.asyncio
    async def test_list_organizations_multiple(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple organizations."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create multiple organizations
        orgs_data = [
            {"name": "Org Alpha", "alias": "org_alpha", "meta": {"priority": 1}},
            {"name": "Org Beta", "alias": "org_beta", "meta": {"priority": 2}},
            {"name": "Org Gamma", "alias": "org_gamma", "meta": {"priority": 3}},
        ]

        for org_data in orgs_data:
            org = KOrganization(
                name=org_data["name"],
                alias=org_data["alias"],
                meta=org_data["meta"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(org)

        await async_session.commit()

        response = await client.get("/organizations")

        assert response.status_code == 200
        data = response.json()
        assert len(data["organizations"]) == 3
        org_names = {org["name"] for org in data["organizations"]}
        assert org_names == {"Org Alpha", "Org Beta", "Org Gamma"}


class TestGetOrganization:
    """Test suite for GET /organizations/{org_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_organization_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test successfully retrieving an organization."""
        response = await client.get(f"/organizations/{test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_organization.id)
        assert data["name"] == "Test Organization"
        assert data["alias"] == "test_org"
        assert data["meta"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_organization_not_found(
        self,
        client: AsyncClient,
    ):
        """Test retrieving a non-existent organization."""
        fake_id = uuid4()
        response = await client.get(f"/organizations/{fake_id}")

        # This will return 403 (forbidden) because the user is not a member of a non-existent org
        # The membership check happens before the existence check
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()


class TestUpdateOrganization:
    """Test suite for PATCH /organizations/{org_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_organization_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization name."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Old Name",
            alias="old_alias",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Add test user as organization principal
        await add_user_to_organization(async_session, org.id, test_user_id)

        # Update name
        update_data = {"name": "New Name"}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["alias"] == "old_alias"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_organization_alias(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization alias."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="old_alias",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Add test user as organization principal
        await add_user_to_organization(async_session, org.id, test_user_id)

        # Update alias
        update_data = {"alias": "new_alias"}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Org"  # Unchanged
        assert data["alias"] == "new_alias"

    @pytest.mark.asyncio
    async def test_update_organization_meta(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization metadata."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Add test user as organization principal
        await add_user_to_organization(async_session, org.id, test_user_id)

        # Update meta
        update_data = {"meta": {"new": "data", "updated": True}}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}

    @pytest.mark.asyncio
    async def test_update_organization_all_fields(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating all organization fields."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Old Name",
            alias="old_alias",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Add test user as organization principal
        await add_user_to_organization(async_session, org.id, test_user_id)

        # Update all fields
        update_data = {
            "name": "New Name",
            "alias": "new_alias",
            "meta": {"new": "data"},
        }
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["alias"] == "new_alias"
        assert data["meta"] == {"new": "data"}

    @pytest.mark.asyncio
    async def test_update_organization_not_found(
        self,
        client: AsyncClient,
    ):
        """Test updating a non-existent organization."""
        fake_id = uuid4()
        update_data = {"name": "New Name"}
        response = await client.patch(f"/organizations/{fake_id}", json=update_data)

        # Returns 403 because user is not a member of non-existent org
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_organization_duplicate_name(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization to a duplicate name fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create two organizations
        org1 = KOrganization(
            name="Org 1",
            alias="org_1",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        org2 = KOrganization(
            name="Org 2",
            alias="org_2",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org1)
        async_session.add(org2)
        await async_session.commit()
        await async_session.refresh(org2)

        # Add test user as organization principal for org2
        await add_user_to_organization(async_session, org2.id, test_user_id)

        # Try to update org2 to have the same name as org1
        update_data = {"name": "Org 1"}
        response = await client.patch(f"/organizations/{org2.id}", json=update_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_organization_duplicate_alias(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization to a duplicate alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create two organizations
        org1 = KOrganization(
            name="Org 1",
            alias="org_1",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        org2 = KOrganization(
            name="Org 2",
            alias="org_2",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org1)
        async_session.add(org2)
        await async_session.commit()
        await async_session.refresh(org2)

        # Add test user as organization principal for org2
        await add_user_to_organization(async_session, org2.id, test_user_id)

        # Try to update org2 to have the same alias as org1
        update_data = {"alias": "org_1"}
        response = await client.patch(f"/organizations/{org2.id}", json=update_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_organization_alias_none(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization with None alias is allowed (no change)."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Add test user as organization principal
        await add_user_to_organization(async_session, org.id, test_user_id)

        # Update with None alias (should be allowed - no change)
        update_data = {"alias": None}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["alias"] == "test_org"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_organization_invalid_alias_empty(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization with empty alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Try to update with empty alias
        update_data = {"alias": ""}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_organization_invalid_alias_special_chars(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization with special characters in alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Try to update with special characters
        update_data = {"alias": "test@domain"}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_organization_invalid_alias_uppercase(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization with uppercase alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Try to update with uppercase alias
        update_data = {"alias": "ABC"}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_organization_invalid_alias_mixed_case(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization with mixed case alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Try to update with mixed case alias (lowercase start, valid chars, but has uppercase)
        # This will pass the isalpha/islower check on first char and all char check
        # but fail the final islower check
        update_data = {"alias": "test_Alias"}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_organization_invalid_alias(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating organization with invalid alias fails."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="Test Org",
            alias="test_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        # Try to update with invalid alias
        update_data = {"alias": "Invalid-Alias"}
        response = await client.patch(f"/organizations/{org.id}", json=update_data)

        assert response.status_code == 422


class TestDeleteOrganization:
    """Test suite for DELETE /organizations/{org_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_organization_success(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting an organization."""
        # Create principal first
        from app.models import KPrincipal
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

        # Create organization
        org = KOrganization(
            name="To Delete",
            alias="to_delete",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(org)
        await async_session.commit()
        await async_session.refresh(org)

        org_id = org.id

        # Add test user as organization principal
        await add_user_to_organization(async_session, org.id, test_user_id)

        # Delete organization
        response = await client.delete(f"/organizations/{org_id}")

        assert response.status_code == 204

        # Verify it's deleted (returns 403 since org no longer exists and user is not a member)
        get_response = await client.get(f"/organizations/{org_id}")
        assert get_response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(
        self,
        client: AsyncClient,
    ):
        """Test deleting a non-existent organization."""
        fake_id = uuid4()
        response = await client.delete(f"/organizations/{fake_id}")

        # Returns 403 because user is not a member of non-existent org
        assert response.status_code == 403


class TestUnauthorizedOrganizationAccess:
    """Test suite for unauthorized organization access scenarios."""

    @pytest.mark.asyncio
    async def test_get_organization_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
    ):
        """Test getting an organization the user is not a member of."""
        response = await client.get(
            f"/organizations/{test_organization_without_membership.id}"
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_organization_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
    ):
        """Test updating an organization the user is not a member of."""
        update_data = {"name": "New Name"}
        response = await client.patch(
            f"/organizations/{test_organization_without_membership.id}",
            json=update_data,
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_organization_unauthorized(
        self,
        client: AsyncClient,
        test_organization_without_membership: KOrganization,
    ):
        """Test deleting an organization the user is not a member of."""
        response = await client.delete(
            f"/organizations/{test_organization_without_membership.id}"
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()


class TestOrganizationDataInconsistency:
    """Test suite for data inconsistency scenarios (membership exists but org doesn't)."""

    @pytest.mark.asyncio
    async def test_get_organization_with_membership_but_no_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting an organization when user is a member but org doesn't exist."""
        # Create principal first
        from app.models import KPrincipal
        from sqlalchemy import text
        from datetime import datetime

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
        await async_session.execute(
            text("PRAGMA foreign_keys = OFF")
        )
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
            }
        )
        await async_session.commit()
        await async_session.execute(
            text("PRAGMA foreign_keys = ON")
        )
        await async_session.commit()

        response = await client.get(f"/organizations/{fake_org_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_organization_with_membership_but_no_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating an organization when user is a member but org doesn't exist."""
        # Create principal first
        from app.models import KPrincipal
        from sqlalchemy import text
        from datetime import datetime

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
        await async_session.execute(
            text("PRAGMA foreign_keys = OFF")
        )
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
            }
        )
        await async_session.commit()
        await async_session.execute(
            text("PRAGMA foreign_keys = ON")
        )
        await async_session.commit()

        update_data = {"name": "New Name"}
        response = await client.patch(f"/organizations/{fake_org_id}", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_organization_with_membership_but_no_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test deleting an organization when user is a member but org doesn't exist."""
        # Create principal first
        from app.models import KPrincipal
        from sqlalchemy import text
        from datetime import datetime

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
        await async_session.execute(
            text("PRAGMA foreign_keys = OFF")
        )
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
            }
        )
        await async_session.commit()
        await async_session.execute(
            text("PRAGMA foreign_keys = ON")
        )
        await async_session.commit()

        response = await client.delete(f"/organizations/{fake_org_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
