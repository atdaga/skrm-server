"""Unit tests for KOrganization model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_organization import KOrganization
from tests.conftest import get_test_org_id


class TestKOrganizationModel:
    """Test suite for KOrganization model."""

    @pytest.mark.asyncio
    async def test_create_organization_with_required_fields(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test creating an organization with only required fields."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Acme Corporation",
            alias="acme_corp",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.id is not None
        assert isinstance(org.id, UUID)
        assert org.name == "Acme Corporation"
        assert org.alias == "acme_corp"

    @pytest.mark.asyncio
    async def test_organization_default_values(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that default values are set correctly."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Tech Inc",
            alias="tech_inc",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.meta == {}
        assert isinstance(org.created, datetime)
        assert isinstance(org.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_organization_with_custom_name(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test creating an organization with a custom name."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Sales Corp",
            alias="sales_corp",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.name == "Sales Corp"
        assert org.alias == "sales_corp"

    @pytest.mark.asyncio
    async def test_organization_with_meta_data(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test creating an organization with metadata."""
        meta_data = {
            "industry": "Technology",
            "location": "San Francisco",
            "employee_count": 500,
        }

        org = KOrganization(
            id=get_test_org_id(),
            name="Backend Corp",
            alias="backend_corp",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.meta == meta_data
        assert org.meta["industry"] == "Technology"
        assert org.meta["location"] == "San Francisco"
        assert org.meta["employee_count"] == 500

    @pytest.mark.asyncio
    async def test_organization_unique_constraint_name(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that name must be unique."""
        org1 = KOrganization(
            id=get_test_org_id(),
            name="Engineering Corp",
            alias="eng_corp",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org1)
        await session.commit()

        # Try to create another organization with same name
        org2 = KOrganization(
            id=get_test_org_id(),
            name="Engineering Corp",
            alias="different_alias",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_organization_unique_constraint_alias(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that alias must be unique."""
        org1 = KOrganization(
            id=get_test_org_id(),
            name="Marketing Corp",
            alias="marketing",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org1)
        await session.commit()

        # Try to create another organization with same alias
        org2 = KOrganization(
            id=get_test_org_id(),
            name="Different Name",
            alias="marketing",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_organization_multiple_organizations(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that multiple organizations can exist with different names and aliases."""
        org1 = KOrganization(
            id=get_test_org_id(),
            name="Engineering Corp A",
            alias="eng_corp_a",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org2 = KOrganization(
            id=get_test_org_id(),
            name="Engineering Corp B",
            alias="eng_corp_b",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org1)
        session.add(org2)
        await session.commit()

        # Both should exist
        result_exec = await session.execute(
            select(KOrganization).where(KOrganization.deleted_at.is_(None))  # type: ignore[comparison-overlap]  # noqa: E712
        )
        organizations = result_exec.scalars().all()
        assert len(organizations) == 2

    @pytest.mark.asyncio
    async def test_organization_different_names_and_aliases(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that organizations with different names and aliases can coexist."""
        org1 = KOrganization(
            id=get_test_org_id(),
            name="Marketing Corp A",
            alias="marketing_a",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org2 = KOrganization(
            id=get_test_org_id(),
            name="Marketing Corp B",
            alias="marketing_b",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org1)
        session.add(org2)
        await session.commit()

        # Both should exist
        result_exec = await session.execute(
            select(KOrganization).where(KOrganization.deleted_at.is_(None))  # type: ignore[comparison-overlap]  # noqa: E712
        )
        organizations = result_exec.scalars().all()
        assert len(organizations) == 2

    @pytest.mark.asyncio
    async def test_organization_query(self, session: AsyncSession, creator_id: UUID):
        """Test querying organizations from database."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Product Corp",
            alias="product_corp",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()

        # Query by name
        result_exec = await session.execute(
            select(KOrganization).where(
                KOrganization.name == "Product Corp",
                KOrganization.deleted_at.is_(None),  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        result = result_exec.scalar_one_or_none()

        assert result is not None
        assert result.name == "Product Corp"
        assert result.alias == "product_corp"

    @pytest.mark.asyncio
    async def test_organization_query_by_alias(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test querying organizations by alias."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Data Corp",
            alias="data_corp",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()

        # Query by alias
        result_exec = await session.execute(
            select(KOrganization).where(
                KOrganization.alias == "data_corp",
                KOrganization.deleted_at.is_(None),  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        result = result_exec.scalar_one_or_none()

        assert result is not None
        assert result.name == "Data Corp"
        assert result.alias == "data_corp"

    @pytest.mark.asyncio
    async def test_organization_query_by_name(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test querying organizations by name."""
        org1 = KOrganization(
            id=get_test_org_id(),
            name="Org A",
            alias="org_a",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org2 = KOrganization(
            id=get_test_org_id(),
            name="Org B",
            alias="org_b",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        org3 = KOrganization(
            id=get_test_org_id(),
            name="Org C",
            alias="org_c",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org1)
        session.add(org2)
        session.add(org3)
        await session.commit()

        # Query specific organization by name
        result_exec = await session.execute(
            select(KOrganization).where(
                KOrganization.name == "Org A",
                KOrganization.deleted_at.is_(None),  # type: ignore[comparison-overlap]  # noqa: E712
            )
        )
        result = result_exec.scalar_one_or_none()

        assert result is not None
        assert result.name == "Org A"
        assert result.alias == "org_a"

    @pytest.mark.asyncio
    async def test_organization_update(self, session: AsyncSession, creator_id: UUID):
        """Test updating organization fields."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Old Name",
            alias="old_alias",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        # Update fields
        org.name = "New Name"
        org.alias = "new_alias"
        org.meta = {"updated": True}
        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.name == "New Name"
        assert org.alias == "new_alias"
        assert org.meta == {"updated": True}

    @pytest.mark.asyncio
    async def test_organization_delete(self, session: AsyncSession, creator_id: UUID):
        """Test deleting an organization."""
        org = KOrganization(
            id=get_test_org_id(),
            name="To Delete",
            alias="to_delete",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        org_id = org.id

        # Delete the organization
        await session.delete(org)
        await session.commit()

        # Verify it's deleted
        result = await session.get(KOrganization, org_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_organization_meta_json_field(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that meta field correctly stores and retrieves complex JSON data."""
        meta_data = {
            "description": "An organization for software development",
            "settings": {
                "notifications": True,
                "auto_assign": False,
            },
            "tags": ["technology", "software", "consulting"],
            "metrics": {
                "employee_count": 100,
                "revenue": 5000000,
            },
        }

        org = KOrganization(
            id=get_test_org_id(),
            name="Complex Meta Org",
            alias="complex_meta_org",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.meta == meta_data
        assert org.meta["description"] == "An organization for software development"
        assert org.meta["settings"]["notifications"] is True
        assert org.meta["tags"] == ["technology", "software", "consulting"]
        assert org.meta["metrics"]["employee_count"] == 100

    @pytest.mark.asyncio
    async def test_organization_list_all(self, session: AsyncSession, creator_id: UUID):
        """Test listing all organizations."""
        orgs_data = [
            {"name": "Org 1", "alias": "org_1"},
            {"name": "Org 2", "alias": "org_2"},
            {"name": "Org 3", "alias": "org_3"},
        ]

        for org_data in orgs_data:
            org = KOrganization(
                id=get_test_org_id(),
                **org_data,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(org)

        await session.commit()

        # List all organizations
        result_exec = await session.execute(
            select(KOrganization).where(KOrganization.deleted_at.is_(None))  # type: ignore[comparison-overlap]  # noqa: E712
        )
        all_orgs = result_exec.scalars().all()
        assert len(all_orgs) == 3

    @pytest.mark.asyncio
    async def test_organization_count_all(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test counting all organizations."""
        # Create multiple organizations
        for i in range(5):
            org = KOrganization(
                id=get_test_org_id(),
                name=f"Org {i}",
                alias=f"org_{i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(org)

        await session.commit()

        # Count all organizations
        result_exec = await session.execute(
            select(KOrganization).where(KOrganization.deleted_at.is_(None))  # type: ignore[comparison-overlap]  # noqa: E712
        )
        all_orgs = result_exec.scalars().all()
        assert len(all_orgs) == 5

    @pytest.mark.asyncio
    async def test_organization_empty_meta(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that organizations can have empty meta dictionaries."""
        org = KOrganization(
            id=get_test_org_id(),
            name="Empty Meta Org",
            alias="empty_meta_org",
            meta={},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        assert org.meta == {}
        assert len(org.meta) == 0

    @pytest.mark.asyncio
    async def test_organization_alias_lowercase(
        self, session: AsyncSession, creator_id: UUID
    ):
        """Test that alias can contain lowercase letters, numbers, and underscores."""
        valid_aliases = [
            "acme",
            "acme_corp",
            "org123",
            "my_org_2",
            "a",
            "abc_def_ghi_123",
        ]

        for i, alias in enumerate(valid_aliases):
            org = KOrganization(
                id=get_test_org_id(),
                name=f"Org {i}",
                alias=alias,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(org)

        await session.commit()

        # All should be created successfully
        result_exec = await session.execute(
            select(KOrganization).where(KOrganization.deleted_at.is_(None))  # type: ignore[comparison-overlap]  # noqa: E712
        )
        all_orgs = result_exec.scalars().all()
        assert len(all_orgs) == len(valid_aliases)
