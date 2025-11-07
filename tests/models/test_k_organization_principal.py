"""Unit tests for KOrganizationPrincipal model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_organization import KOrganization
from app.models.k_organization_principal import KOrganizationPrincipal
from app.models.k_principal import KPrincipal


class TestKOrganizationPrincipalModel:
    """Test suite for KOrganizationPrincipal model."""

    @pytest.fixture
    async def organization(
        self, session: AsyncSession, creator_id: UUID
    ) -> KOrganization:
        """Create a test organization."""
        organization = KOrganization(
            name="Test Organization",
            alias="test-org",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(organization)
        await session.commit()
        await session.refresh(organization)
        return organization

    @pytest.fixture
    async def principal(self, session: AsyncSession, creator_id: UUID) -> KPrincipal:
        """Create a test principal."""
        principal = KPrincipal(
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(principal)
        await session.commit()
        await session.refresh(principal)
        return principal

    @pytest.mark.asyncio
    async def test_create_organization_principal_with_required_fields(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test creating an organization principal with only required fields."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()
        await session.refresh(org_principal)

        assert org_principal.org_id == organization.id
        assert org_principal.principal_id == principal.id

    @pytest.mark.asyncio
    async def test_organization_principal_default_values(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that default values are set correctly."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()
        await session.refresh(org_principal)

        assert org_principal.role is None
        assert org_principal.meta == {}
        assert isinstance(org_principal.created, datetime)
        assert isinstance(org_principal.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_organization_principal_with_role(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test creating an organization principal with a role."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()
        await session.refresh(org_principal)

        assert org_principal.role == "admin"

    @pytest.mark.asyncio
    async def test_organization_principal_with_meta_data(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test creating an organization principal with metadata."""
        meta_data = {
            "join_date": "2024-01-01",
            "department": "Engineering",
            "level": "Senior",
        }

        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="engineer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()
        await session.refresh(org_principal)

        assert org_principal.meta == meta_data
        assert org_principal.meta["department"] == "Engineering"
        assert org_principal.meta["level"] == "Senior"

    @pytest.mark.asyncio
    async def test_organization_principal_composite_primary_key(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that org_id + principal_id form a composite primary key."""
        org_principal1 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(org_principal1)

        # Try to create another membership with same org_id + principal_id
        org_principal2 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="different_role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_principal_multiple_organizations(
        self, session: AsyncSession, principal: KPrincipal, creator_id: UUID
    ):
        """Test that a principal can be a member of multiple organizations."""
        org1 = KOrganization(
            name="Organization 1",
            alias="org-1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        org2 = KOrganization(
            name="Organization 2",
            alias="org-2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(org1)
        session.add(org2)
        await session.commit()

        principal1 = KOrganizationPrincipal(
            org_id=org1.id,
            principal_id=principal.id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        principal2 = KOrganizationPrincipal(
            org_id=org2.id,
            principal_id=principal.id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal1)
        session.add(principal2)
        await session.commit()

        # Query all organizations for this principal
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.principal_id == principal.id
            )
        )
        memberships = result_exec.scalars().all()

        assert len(memberships) == 2
        roles = {m.role for m in memberships}
        assert roles == {"admin", "member"}

    @pytest.mark.asyncio
    async def test_organization_multiple_principals(
        self, session: AsyncSession, organization: KOrganization, creator_id: UUID
    ):
        """Test that an organization can have multiple principals."""
        principal1 = KPrincipal(
            username="user1",
            primary_email="user1@example.com",
            first_name="User",
            last_name="One",
            display_name="User One",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        principal2 = KPrincipal(
            username="user2",
            primary_email="user2@example.com",
            first_name="User",
            last_name="Two",
            display_name="User Two",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal1)
        session.add(principal2)
        await session.commit()

        org_principal1 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal1.id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org_principal2 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal2.id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal1)
        session.add(org_principal2)
        await session.commit()

        # Query all principals of this organization
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == organization.id
            )
        )
        principals = result_exec.scalars().all()

        assert len(principals) == 2
        roles = {p.role for p in principals}
        assert roles == {"admin", "member"}

    @pytest.mark.asyncio
    async def test_organization_principal_query_by_role(
        self, session: AsyncSession, organization: KOrganization, creator_id: UUID
    ):
        """Test querying organization principals by role."""
        principals = []
        for i in range(3):
            principal = KPrincipal(
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name="User",
                last_name=f"{i}",
                display_name=f"User {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            principals.append(principal)
            session.add(principal)

        await session.commit()

        # Add principals with different roles
        org_principal1 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principals[0].id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org_principal2 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principals[1].id,
            role="admin",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org_principal3 = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principals[2].id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal1)
        session.add(org_principal2)
        session.add(org_principal3)
        await session.commit()

        # Query admins
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == organization.id,
                KOrganizationPrincipal.role == "admin",
            )
        )
        admins = result_exec.scalars().all()

        assert len(admins) == 2

    @pytest.mark.asyncio
    async def test_organization_principal_update(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test updating organization principal fields."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="member",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()

        # Update role
        org_principal.role = "admin"
        org_principal.meta = {"promoted": True}
        session.add(org_principal)
        await session.commit()
        await session.refresh(org_principal)

        assert org_principal.role == "admin"
        assert org_principal.meta == {"promoted": True}

    @pytest.mark.asyncio
    async def test_organization_principal_delete(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test deleting an organization principal."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()

        # Delete the organization principal
        await session.delete(org_principal)
        await session.commit()

        # Verify it's deleted
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == organization.id,
                KOrganizationPrincipal.principal_id == principal.id,
            )
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

    @pytest.mark.asyncio
    async def test_cascade_delete_organization(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that deleting an organization cascades to organization principals but not the principal."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()

        # Delete the organization
        await session.delete(organization)
        await session.commit()

        # Verify organization principal is also deleted
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == organization.id
            )
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify principal still exists
        await session.refresh(principal)
        assert principal.id == principal.id

    @pytest.mark.asyncio
    async def test_cascade_delete_principal(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that deleting a principal cascades to organization principals but not the organization."""
        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()

        # Delete the principal
        await session.delete(principal)
        await session.commit()

        # Verify organization principal is also deleted
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.principal_id == principal.id
            )
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify organization still exists
        await session.refresh(organization)
        assert organization.id == organization.id

    @pytest.mark.asyncio
    async def test_organization_principal_meta_json_field(
        self,
        session: AsyncSession,
        organization: KOrganization,
        principal: KPrincipal,
        creator_id: UUID,
    ):
        """Test that meta field correctly stores and retrieves JSON data."""
        meta_data = {
            "permissions": ["read", "write", "delete"],
            "settings": {
                "notifications": True,
                "auto_assign": False,
            },
            "stats": {
                "tasks_completed": 42,
                "reviews_done": 15,
            },
        }

        org_principal = KOrganizationPrincipal(
            org_id=organization.id,
            principal_id=principal.id,
            role="engineer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org_principal)
        await session.commit()
        await session.refresh(org_principal)

        assert org_principal.meta == meta_data
        assert org_principal.meta["permissions"] == ["read", "write", "delete"]
        assert org_principal.meta["settings"]["notifications"] is True
        assert org_principal.meta["stats"]["tasks_completed"] == 42

    @pytest.mark.asyncio
    async def test_organization_principal_count(
        self, session: AsyncSession, organization: KOrganization, creator_id: UUID
    ):
        """Test counting organization principals."""
        principals = []
        for i in range(5):
            principal = KPrincipal(
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name="User",
                last_name=f"{i}",
                display_name=f"User {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            principals.append(principal)
            session.add(principal)

        await session.commit()

        # Add all principals to the organization
        for principal in principals:
            org_principal = KOrganizationPrincipal(
                org_id=organization.id,
                principal_id=principal.id,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(org_principal)

        await session.commit()

        # Count principals
        result_exec = await session.execute(
            select(KOrganizationPrincipal).where(
                KOrganizationPrincipal.org_id == organization.id
            )
        )
        org_principals = result_exec.scalars().all()

        assert len(org_principals) == 5
