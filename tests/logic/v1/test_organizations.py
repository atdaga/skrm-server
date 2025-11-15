"""Unit tests for organization business logic."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import OrganizationAlreadyExistsException
from app.logic.v1.organizations import create_organization
from app.models import KOrganization
from app.models.k_principal import SystemRole
from app.schemas.organization import OrganizationCreate


class TestCreateOrganization:
    """Test suite for create_organization logic function."""

    @pytest.mark.asyncio
    async def test_create_organization_success(
        self,
        async_session: AsyncSession,
        test_user_id,
        test_scope,
    ):
        """Test successfully creating a new organization."""
        # Arrange
        org_data = OrganizationCreate(
            name="Acme Corporation",
            alias="acme_corp",
            meta={"industry": "Technology"},
        )

        # Act
        result = await create_organization(
            org_data=org_data,
            user_id=test_user_id,
            scope=test_scope,
            system_role=SystemRole.SYSTEM_ROOT,
            db=async_session,
        )

        # Assert
        assert isinstance(result, KOrganization)
        assert result.name == "Acme Corporation"
        assert result.alias == "acme_corp"
        assert result.meta == {"industry": "Technology"}
        assert result.created_by == test_user_id
        assert result.last_modified_by == test_user_id
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_name_error(
        self,
        async_session: AsyncSession,
        test_user_id,
        test_scope,
    ):
        """Test creating an organization with a duplicate name raises exception."""
        # Arrange - create first organization
        org_data = OrganizationCreate(
            name="Acme Corporation",
            alias="acme_corp",
            meta={},
        )
        await create_organization(
            org_data=org_data,
            user_id=test_user_id,
            scope=test_scope,
            system_role=SystemRole.SYSTEM_ROOT,
            db=async_session,
        )

        # Act & Assert - attempt to create duplicate
        duplicate_data = OrganizationCreate(
            name="Acme Corporation",  # Same name
            alias="acme_different",  # Different alias
            meta={},
        )

        with pytest.raises(OrganizationAlreadyExistsException) as exc_info:
            await create_organization(
                org_data=duplicate_data,
                user_id=test_user_id,
                scope=test_scope,
                system_role=SystemRole.SYSTEM_ROOT,
                db=async_session,
            )

        assert "Acme Corporation" in str(exc_info.value)
