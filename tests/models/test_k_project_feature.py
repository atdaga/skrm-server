"""Unit tests for KProjectFeature model."""

from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KFeature, KProject, KProjectFeature
from app.models.k_feature import FeatureType
from tests.conftest import get_test_feature_id


class TestKProjectFeatureModel:
    """Test suite for KProjectFeature model."""

    @pytest.fixture
    async def project(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KProject:
        """Create a test project."""
        project = KProject(
            name="Test Project",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project

    @pytest.fixture
    async def feature(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KFeature:
        """Create a test feature."""
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
    async def test_create_project_feature_with_required_fields(
        self,
        session: AsyncSession,
        project: KProject,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a project feature with only required fields."""
        project_feature = KProjectFeature(
            project_id=project.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_feature)
        await session.commit()
        await session.refresh(project_feature)

        assert project_feature.project_id == project.id
        assert project_feature.feature_id == feature.id
        assert project_feature.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_project_feature_composite_primary_key(
        self,
        session: AsyncSession,
        project: KProject,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that project_id and feature_id form a composite primary key."""
        project_feature1 = KProjectFeature(
            project_id=project.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_feature1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(project_feature1)

        # Try to create another project_feature with the same project_id and feature_id
        project_feature2 = KProjectFeature(
            project_id=project.id,
            feature_id=feature.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_feature2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete_from_project(
        self,
        session: AsyncSession,
        project: KProject,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a project cascades to project features but not the feature."""
        project_feature = KProjectFeature(
            project_id=project.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_feature)
        await session.commit()

        # Delete the project
        await session.delete(project)
        await session.commit()

        # Verify project feature is deleted
        result_exec = await session.execute(
            select(KProjectFeature).where(KProjectFeature.project_id == project.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify feature still exists
        await session.refresh(feature)
        assert feature.id == feature.id

    @pytest.mark.asyncio
    async def test_cascade_delete_from_feature(
        self,
        session: AsyncSession,
        project: KProject,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a feature cascades to project features but not the project."""
        project_feature = KProjectFeature(
            project_id=project.id,
            feature_id=feature.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project_feature)
        await session.commit()

        # Delete the feature
        await session.delete(feature)
        await session.commit()

        # Verify project feature is deleted
        result_exec = await session.execute(
            select(KProjectFeature).where(KProjectFeature.feature_id == feature.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify project still exists
        await session.refresh(project)
        assert project.id == project.id
