"""Unit tests for KTaskFeature model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KFeature, KTask, KTaskFeature, KTeam
from tests.conftest import get_test_feature_id, get_test_task_id


class TestKTaskFeatureModel:
    """Test suite for KTaskFeature model."""

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
            id=get_test_task_id(test_org_id),
            summary="Test Task",
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
    async def feature(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KFeature:
        """Create a test feature."""
        from app.models.k_feature import FeatureType

        feature = KFeature(
            id=get_test_feature_id(test_org_id),
            name="Test Feature",
            org_id=test_org_id,
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(feature)
        await session.commit()
        await session.refresh(feature)
        return feature

    @pytest.mark.asyncio
    async def test_create_task_feature_with_required_fields(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task feature with only required fields."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()
        await session.refresh(task_feature)

        assert task_feature.task_id == task.id
        assert task_feature.feature_id == feature.id
        assert task_feature.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_task_feature_default_values(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()
        await session.refresh(task_feature)

        assert task_feature.role is None
        assert task_feature.meta == {}
        assert isinstance(task_feature.created, datetime)
        assert isinstance(task_feature.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_task_feature_with_role(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task feature with a role."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="implements",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()
        await session.refresh(task_feature)

        assert task_feature.role == "implements"

    @pytest.mark.asyncio
    async def test_task_feature_with_meta_data(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task feature with metadata."""
        meta_data = {
            "completion_percentage": 75,
            "priority": "high",
            "tags": ["frontend", "ui"],
        }

        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="implements",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()
        await session.refresh(task_feature)

        assert task_feature.meta == meta_data

    @pytest.mark.asyncio
    async def test_task_feature_composite_primary_key(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that task_id and feature_id form a composite primary key."""
        task_feature1 = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(task_feature1)

        # Try to create another task_feature with the same task_id and feature_id
        task_feature2 = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_task_feature_audit_fields(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="implements",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()
        await session.refresh(task_feature)

        assert task_feature.created_by == creator_id
        assert task_feature.last_modified_by == creator_id

        # Update the task feature
        task_feature.role = "extends"
        task_feature.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(task_feature)

        assert task_feature.created_by == creator_id  # Should not change
        assert task_feature.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_task_feature_cascade_delete_from_task(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a task cascades to task features but not the feature."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()

        # Delete the task
        await session.delete(task)
        await session.commit()

        # Verify task feature is deleted
        result_exec = await session.execute(
            select(KTaskFeature).where(KTaskFeature.task_id == task.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify feature still exists
        await session.refresh(feature)
        assert feature.id == feature.id

    @pytest.mark.asyncio
    async def test_task_feature_cascade_delete_from_feature(
        self,
        session: AsyncSession,
        task: KTask,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a feature cascades to task features but not the task."""
        task_feature = KTaskFeature(
            task_id=task.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_feature)
        await session.commit()

        # Delete the feature
        await session.delete(feature)
        await session.commit()

        # Verify task feature is deleted
        result_exec = await session.execute(
            select(KTaskFeature).where(KTaskFeature.feature_id == feature.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify task still exists
        await session.refresh(task)
        assert task.id == task.id
