"""Unit tests for KTaskDeploymentEnv model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KDeploymentEnv, KTask, KTaskDeploymentEnv, KTeam


class TestKTaskDeploymentEnvModel:
    """Test suite for KTaskDeploymentEnv model."""

    @pytest.fixture
    async def team(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KTeam:
        """Create a test team."""
        team = KTeam(
            name="Test Team",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team)
        await session.commit()
        await session.refresh(team)
        return team

    @pytest.fixture
    async def task(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ) -> KTask:
        """Create a test task."""
        task = KTask(
            name="Test Task",
            org_id=test_org_id,
            team_id=team.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    @pytest.fixture
    async def deployment_env(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KDeploymentEnv:
        """Create a test deployment environment."""
        deployment_env = KDeploymentEnv(
            name="Test Environment",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(deployment_env)
        await session.commit()
        await session.refresh(deployment_env)
        return deployment_env

    @pytest.mark.asyncio
    async def test_create_task_deployment_env_with_required_fields(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task deployment environment with only required fields."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()
        await session.refresh(task_deployment_env)

        assert task_deployment_env.task_id == task.id
        assert task_deployment_env.deployment_env_id == deployment_env.id
        assert task_deployment_env.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_task_deployment_env_default_values(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()
        await session.refresh(task_deployment_env)

        assert task_deployment_env.role is None
        assert task_deployment_env.meta == {}
        assert isinstance(task_deployment_env.created, datetime)
        assert isinstance(task_deployment_env.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_task_deployment_env_with_role(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task deployment environment with a role."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="target",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()
        await session.refresh(task_deployment_env)

        assert task_deployment_env.role == "target"

    @pytest.mark.asyncio
    async def test_task_deployment_env_with_meta_data(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task deployment environment with metadata."""
        meta_data = {
            "deployment_order": 1,
            "auto_deploy": True,
            "notifications": ["email", "slack"],
        }

        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="primary",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()
        await session.refresh(task_deployment_env)

        assert task_deployment_env.meta == meta_data

    @pytest.mark.asyncio
    async def test_task_deployment_env_composite_primary_key(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that task_id and deployment_env_id form a composite primary key."""
        task_deployment_env1 = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(task_deployment_env1)

        # Try to create another task_deployment_env with the same task_id and deployment_env_id
        task_deployment_env2 = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_task_deployment_env_audit_fields(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            role="primary",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()
        await session.refresh(task_deployment_env)

        assert task_deployment_env.created_by == creator_id
        assert task_deployment_env.last_modified_by == creator_id

        # Update the task deployment environment
        task_deployment_env.role = "secondary"
        task_deployment_env.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(task_deployment_env)

        assert task_deployment_env.created_by == creator_id  # Should not change
        assert task_deployment_env.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_task_deployment_env_cascade_delete_from_task(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a task cascades to task deployment environments but not the deployment environment."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()

        # Delete the task
        await session.delete(task)
        await session.commit()

        # Verify task deployment environment is deleted
        result_exec = await session.execute(
            select(KTaskDeploymentEnv).where(KTaskDeploymentEnv.task_id == task.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify deployment environment still exists
        await session.refresh(deployment_env)
        assert deployment_env.id == deployment_env.id

    @pytest.mark.asyncio
    async def test_task_deployment_env_cascade_delete_from_deployment_env(
        self,
        session: AsyncSession,
        task: KTask,
        deployment_env: KDeploymentEnv,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a deployment environment cascades to task deployment environments but not the task."""
        task_deployment_env = KTaskDeploymentEnv(
            task_id=task.id,
            deployment_env_id=deployment_env.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_deployment_env)
        await session.commit()

        # Delete the deployment environment
        await session.delete(deployment_env)
        await session.commit()

        # Verify task deployment environment is deleted
        result_exec = await session.execute(
            select(KTaskDeploymentEnv).where(
                KTaskDeploymentEnv.deployment_env_id == deployment_env.id
            )
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify task still exists
        await session.refresh(task)
        assert task.id == task.id
