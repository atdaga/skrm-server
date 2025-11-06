"""Unit tests for KDeploymentEnv model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_deployment_env import KDeploymentEnv


class TestKDeploymentEnvModel:
    """Test suite for KDeploymentEnv model."""

    @pytest.mark.asyncio
    async def test_create_deployment_env_with_required_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a deployment environment with only required fields."""
        deployment_env = KDeploymentEnv(
            org_id=test_org_id,
            name="Production",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env)
        await session.commit()
        await session.refresh(deployment_env)

        assert deployment_env.id is not None
        assert isinstance(deployment_env.id, UUID)
        assert deployment_env.name == "Production"

    @pytest.mark.asyncio
    async def test_deployment_env_default_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that default values are set correctly."""
        deployment_env = KDeploymentEnv(
            org_id=test_org_id,
            name="Staging",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env)
        await session.commit()
        await session.refresh(deployment_env)

        assert deployment_env.org_id == test_org_id
        assert deployment_env.meta == {}
        assert isinstance(deployment_env.created, datetime)
        assert isinstance(deployment_env.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_deployment_env_with_meta_data(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a deployment environment with metadata."""
        meta_data = {
            "region": "us-east-1",
            "cluster": "main",
            "replicas": 3,
        }

        deployment_env = KDeploymentEnv(
            org_id=test_org_id,
            name="Development",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env)
        await session.commit()
        await session.refresh(deployment_env)

        assert deployment_env.meta == meta_data

    @pytest.mark.asyncio
    async def test_deployment_env_unique_name_per_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that deployment environment names must be unique per organization."""
        deployment_env1 = KDeploymentEnv(
            org_id=test_org_id,
            name="QA",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env1)
        await session.commit()

        # Try to create another deployment environment with the same name in the same org
        deployment_env2 = KDeploymentEnv(
            org_id=test_org_id,
            name="QA",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_deployment_env_same_name_different_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that deployment environment names can be the same across different organizations."""
        other_org_id = UUID("22222222-2222-2222-2222-222222222222")

        deployment_env1 = KDeploymentEnv(
            org_id=test_org_id,
            name="Production",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        deployment_env2 = KDeploymentEnv(
            org_id=other_org_id,
            name="Production",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env1)
        session.add(deployment_env2)
        await session.commit()
        await session.refresh(deployment_env1)
        await session.refresh(deployment_env2)

        assert deployment_env1.name == deployment_env2.name
        assert deployment_env1.org_id != deployment_env2.org_id

    @pytest.mark.asyncio
    async def test_deployment_env_audit_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("33333333-3333-3333-3333-333333333333")

        deployment_env = KDeploymentEnv(
            org_id=test_org_id,
            name="Integration",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(deployment_env)
        await session.commit()
        await session.refresh(deployment_env)

        assert deployment_env.created_by == creator_id
        assert deployment_env.last_modified_by == creator_id

        # Update the deployment environment
        deployment_env.name = "Integration Updated"
        deployment_env.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(deployment_env)

        assert deployment_env.created_by == creator_id  # Should not change
        assert deployment_env.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_query_deployment_envs_by_org_id(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying deployment environments by organization ID."""
        other_org_id = UUID("44444444-4444-4444-4444-444444444444")

        # Create deployment environments in different organizations
        deployment_env1 = KDeploymentEnv(
            org_id=test_org_id,
            name="Prod",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        deployment_env2 = KDeploymentEnv(
            org_id=test_org_id,
            name="Stage",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        deployment_env3 = KDeploymentEnv(
            org_id=other_org_id,
            name="Dev",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add_all([deployment_env1, deployment_env2, deployment_env3])
        await session.commit()

        # Query deployment environments for test_org_id
        stmt = select(KDeploymentEnv).where(KDeploymentEnv.org_id == test_org_id)  # type: ignore[arg-type]
        result = await session.execute(stmt)
        deployment_envs = result.scalars().all()

        assert len(deployment_envs) == 2
        assert all(d.org_id == test_org_id for d in deployment_envs)
