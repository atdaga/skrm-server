"""Unit tests for KFeature model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_feature import FeatureType, KFeature, ReviewResult


class TestKFeatureModel:
    """Test suite for KFeature model."""

    @pytest.mark.asyncio
    async def test_create_feature_with_required_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a feature with only required fields."""
        feature = KFeature(
            org_id=test_org_id,
            name="User Authentication",
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature)
        await session.commit()
        await session.refresh(feature)

        assert feature.id is not None
        assert isinstance(feature.id, UUID)
        assert feature.name == "User Authentication"
        assert feature.feature_type == FeatureType.ENGINEERING

    @pytest.mark.asyncio
    async def test_feature_default_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that default values are set correctly."""
        feature = KFeature(
            org_id=test_org_id,
            name="Dashboard UI",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature)
        await session.commit()
        await session.refresh(feature)

        assert feature.org_id == test_org_id
        assert feature.parent is None
        assert feature.parent_path is None
        assert feature.summary is None
        assert feature.notes is None
        assert feature.guestimate is None
        assert feature.derived_guestimate is None
        assert feature.review_result is None
        assert feature.meta == {}
        assert isinstance(feature.created, datetime)
        assert isinstance(feature.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_feature_with_all_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a feature with all fields populated."""
        parent_feature = KFeature(
            org_id=test_org_id,
            name="Parent Feature",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(parent_feature)
        await session.commit()
        await session.refresh(parent_feature)

        feature = KFeature(
            org_id=test_org_id,
            name="Child Feature",
            parent=parent_feature.id,
            parent_path="/parent",
            feature_type=FeatureType.ENGINEERING,
            summary="This is a summary",
            notes="These are some detailed notes",
            guestimate=5.5,
            derived_guestimate=6.0,
            review_result=ReviewResult.PASSED,
            meta={"priority": "high", "tags": ["urgent"]},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature)
        await session.commit()
        await session.refresh(feature)

        assert feature.parent == parent_feature.id
        assert feature.parent_path == "/parent"
        assert feature.summary == "This is a summary"
        assert feature.notes == "These are some detailed notes"
        assert feature.guestimate == 5.5
        assert feature.derived_guestimate == 6.0
        assert feature.review_result == ReviewResult.PASSED
        assert feature.meta == {"priority": "high", "tags": ["urgent"]}

    @pytest.mark.asyncio
    async def test_feature_unique_name_per_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that feature names must be unique per organization."""
        feature1 = KFeature(
            org_id=test_org_id,
            name="Duplicate Feature",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature1)
        await session.commit()

        # Try to create another feature with the same name in the same org
        feature2 = KFeature(
            org_id=test_org_id,
            name="Duplicate Feature",
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_feature_same_name_different_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that feature names can be the same across different organizations."""
        from app.models import KOrganization

        # Create a second organization
        other_org = KOrganization(
            name="Other Organization",
            alias="other_org",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(other_org)
        await session.commit()
        await session.refresh(other_org)

        feature1 = KFeature(
            org_id=test_org_id,
            name="Payment Gateway",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature2 = KFeature(
            org_id=other_org.id,
            name="Payment Gateway",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature1)
        session.add(feature2)
        await session.commit()
        await session.refresh(feature1)
        await session.refresh(feature2)

        assert feature1.name == feature2.name
        assert feature1.org_id != feature2.org_id

    @pytest.mark.asyncio
    async def test_feature_enum_types(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that feature type and review result enums work correctly."""
        # Test Product feature type
        product_feature = KFeature(
            org_id=test_org_id,
            name="Product Feature",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(product_feature)
        await session.commit()
        await session.refresh(product_feature)
        assert product_feature.feature_type == FeatureType.PRODUCT

        # Test Engineering feature type
        eng_feature = KFeature(
            org_id=test_org_id,
            name="Engineering Feature",
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(eng_feature)
        await session.commit()
        await session.refresh(eng_feature)
        assert eng_feature.feature_type == FeatureType.ENGINEERING

        # Test different review results
        for result in [
            ReviewResult.QUEUED,
            ReviewResult.REVIEWING,
            ReviewResult.PASSED,
            ReviewResult.FAILED,
            ReviewResult.SKIPPED,
        ]:
            feature = KFeature(
                org_id=test_org_id,
                name=f"Feature {result.value}",
                feature_type=FeatureType.PRODUCT,
                review_result=result,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(feature)
        await session.commit()

    @pytest.mark.asyncio
    async def test_feature_audit_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("33333333-3333-3333-3333-333333333333")

        feature = KFeature(
            org_id=test_org_id,
            name="Audited Feature",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature)
        await session.commit()
        await session.refresh(feature)

        assert feature.created_by == creator_id
        assert feature.last_modified_by == creator_id

        # Update the feature
        feature.name = "Updated Feature"
        feature.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(feature)

        assert feature.created_by == creator_id  # Should not change
        assert feature.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_query_features_by_org_id(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying features by organization ID."""
        from app.models import KOrganization

        # Create a second organization
        other_org = KOrganization(
            name="Other Organization",
            alias="other_org_query",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(other_org)
        await session.commit()
        await session.refresh(other_org)

        # Create features in different organizations
        feature1 = KFeature(
            org_id=test_org_id,
            name="Feature 1",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature2 = KFeature(
            org_id=test_org_id,
            name="Feature 2",
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature3 = KFeature(
            org_id=other_org.id,
            name="Feature 3",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add_all([feature1, feature2, feature3])
        await session.commit()

        # Query features for test_org_id
        stmt = select(KFeature).where(
            KFeature.org_id == test_org_id,  # type: ignore[arg-type]
            KFeature.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
        )
        result = await session.execute(stmt)
        features = result.scalars().all()

        assert len(features) == 2
        assert all(f.org_id == test_org_id for f in features)

    @pytest.mark.asyncio
    async def test_feature_parent_relationship(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test parent-child feature relationships."""
        # Create parent feature
        parent = KFeature(
            org_id=test_org_id,
            name="Parent Feature",
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(parent)
        await session.commit()
        await session.refresh(parent)

        # Create child features
        child1 = KFeature(
            org_id=test_org_id,
            name="Child Feature 1",
            parent=parent.id,
            parent_path=f"/{parent.name}",
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        child2 = KFeature(
            org_id=test_org_id,
            name="Child Feature 2",
            parent=parent.id,
            parent_path=f"/{parent.name}",
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add_all([child1, child2])
        await session.commit()
        await session.refresh(child1)
        await session.refresh(child2)

        # Query children by parent
        stmt = select(KFeature).where(
            KFeature.parent == parent.id,  # type: ignore[arg-type]
            KFeature.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
        )
        result = await session.execute(stmt)
        children = result.scalars().all()

        assert len(children) == 2
        assert all(c.parent == parent.id for c in children)
