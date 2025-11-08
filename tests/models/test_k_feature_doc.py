"""Unit tests for KFeatureDoc model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_doc import KDoc
from app.models.k_feature import FeatureType, KFeature
from app.models.k_feature_doc import KFeatureDoc


class TestKFeatureDocModel:
    """Test suite for KFeatureDoc model."""

    @pytest.fixture
    async def feature(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KFeature:
        """Create a test feature."""
        feature = KFeature(
            name="User Authentication",
            org_id=test_org_id,
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(feature)
        await session.commit()
        await session.refresh(feature)
        return feature

    @pytest.fixture
    async def doc(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KDoc:
        """Create a test doc."""
        doc = KDoc(
            name="Authentication Spec",
            org_id=test_org_id,
            content="This is the authentication specification",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc

    @pytest.mark.asyncio
    async def test_create_feature_doc_with_required_fields(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a feature doc with only required fields."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()
        await session.refresh(feature_doc)

        assert feature_doc.feature_id == feature.id
        assert feature_doc.doc_id == doc.id
        assert feature_doc.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_feature_doc_default_values(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()
        await session.refresh(feature_doc)

        assert feature_doc.role is None
        assert feature_doc.meta == {}
        assert isinstance(feature_doc.created, datetime)
        assert isinstance(feature_doc.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_feature_doc_with_role(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a feature doc with a role."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="specification",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()
        await session.refresh(feature_doc)

        assert feature_doc.role == "specification"

    @pytest.mark.asyncio
    async def test_feature_doc_with_meta_data(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a feature doc with metadata."""
        meta_data = {
            "version": "1.0",
            "status": "draft",
            "priority": "high",
        }

        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="requirement",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()
        await session.refresh(feature_doc)

        assert feature_doc.meta == meta_data
        assert feature_doc.meta["version"] == "1.0"
        assert feature_doc.meta["status"] == "draft"

    @pytest.mark.asyncio
    async def test_feature_doc_composite_primary_key(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that feature_id + doc_id form a composite primary key."""
        feature_doc1 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(feature_doc1)

        # Try to create another relationship with same feature_id + doc_id
        feature_doc2 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="different_role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_doc_multiple_features(
        self,
        session: AsyncSession,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that a doc can be associated with multiple features."""
        feature1 = KFeature(
            name="Feature One",
            org_id=test_org_id,
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        feature2 = KFeature(
            name="Feature Two",
            org_id=test_org_id,
            feature_type=FeatureType.ENGINEERING,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(feature1)
        session.add(feature2)
        await session.commit()

        feature_doc1 = KFeatureDoc(
            feature_id=feature1.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="specification",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature_doc2 = KFeatureDoc(
            feature_id=feature2.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="reference",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc1)
        session.add(feature_doc2)
        await session.commit()

        # Query all features for this doc
        result_exec = await session.execute(
            select(KFeatureDoc).where(KFeatureDoc.doc_id == doc.id)
        )
        relationships = result_exec.scalars().all()

        assert len(relationships) == 2
        roles = {r.role for r in relationships}
        assert roles == {"specification", "reference"}

    @pytest.mark.asyncio
    async def test_feature_multiple_docs(
        self,
        session: AsyncSession,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that a feature can have multiple docs."""
        doc1 = KDoc(
            name="Doc One",
            org_id=test_org_id,
            content="First document content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        doc2 = KDoc(
            name="Doc Two",
            org_id=test_org_id,
            content="Second document content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc1)
        session.add(doc2)
        await session.commit()

        feature_doc1 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc1.id,
            org_id=test_org_id,
            role="main",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature_doc2 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc2.id,
            org_id=test_org_id,
            role="supplementary",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc1)
        session.add(feature_doc2)
        await session.commit()

        # Query all docs for this feature
        result_exec = await session.execute(
            select(KFeatureDoc).where(KFeatureDoc.feature_id == feature.id)
        )
        docs = result_exec.scalars().all()

        assert len(docs) == 2
        roles = {d.role for d in docs}
        assert roles == {"main", "supplementary"}

    @pytest.mark.asyncio
    async def test_feature_doc_query_by_role(
        self,
        session: AsyncSession,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test querying feature docs by role."""
        docs = []
        for i in range(3):
            doc = KDoc(
                name=f"Doc {i}",
                org_id=test_org_id,
                content=f"Content {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            docs.append(doc)
            session.add(doc)

        await session.commit()

        # Add docs with different roles
        feature_doc1 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=docs[0].id,
            org_id=test_org_id,
            role="specification",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature_doc2 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=docs[1].id,
            org_id=test_org_id,
            role="specification",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        feature_doc3 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=docs[2].id,
            org_id=test_org_id,
            role="reference",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc1)
        session.add(feature_doc2)
        session.add(feature_doc3)
        await session.commit()

        # Query specifications
        result_exec = await session.execute(
            select(KFeatureDoc).where(
                KFeatureDoc.feature_id == feature.id,
                KFeatureDoc.role == "specification",
            )
        )
        specs = result_exec.scalars().all()

        assert len(specs) == 2

    @pytest.mark.asyncio
    async def test_feature_doc_update(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test updating feature doc fields."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="draft",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()

        # Update role
        feature_doc.role = "final"
        feature_doc.meta = {"approved": True}
        session.add(feature_doc)
        await session.commit()
        await session.refresh(feature_doc)

        assert feature_doc.role == "final"
        assert feature_doc.meta == {"approved": True}

    @pytest.mark.asyncio
    async def test_feature_doc_delete(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test deleting a feature doc."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()

        # Delete the feature doc
        await session.delete(feature_doc)
        await session.commit()

        # Verify it's deleted
        result_exec = await session.execute(
            select(KFeatureDoc).where(
                KFeatureDoc.feature_id == feature.id,
                KFeatureDoc.doc_id == doc.id,
            )
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

    @pytest.mark.asyncio
    async def test_cascade_delete_feature(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a feature cascades to feature docs but not the doc."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()

        # Delete the feature
        await session.delete(feature)
        await session.commit()

        # Verify feature doc is also deleted
        result_exec = await session.execute(
            select(KFeatureDoc).where(KFeatureDoc.feature_id == feature.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify doc still exists
        await session.refresh(doc)
        assert doc.id == doc.id

    @pytest.mark.asyncio
    async def test_cascade_delete_doc(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a doc cascades to feature docs but not the feature."""
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()

        # Delete the doc
        await session.delete(doc)
        await session.commit()

        # Verify feature doc is also deleted
        result_exec = await session.execute(
            select(KFeatureDoc).where(KFeatureDoc.doc_id == doc.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify feature still exists
        await session.refresh(feature)
        assert feature.id == feature.id

    @pytest.mark.asyncio
    async def test_feature_doc_meta_json_field(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that meta field correctly stores and retrieves JSON data."""
        meta_data = {
            "tags": ["authentication", "security", "oauth"],
            "settings": {
                "auto_update": True,
                "notify_changes": False,
            },
            "stats": {
                "views": 42,
                "edits": 15,
            },
        }

        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="specification",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc)
        await session.commit()
        await session.refresh(feature_doc)

        assert feature_doc.meta == meta_data
        assert feature_doc.meta["tags"] == ["authentication", "security", "oauth"]
        assert feature_doc.meta["settings"]["auto_update"] is True
        assert feature_doc.meta["stats"]["views"] == 42

    @pytest.mark.asyncio
    async def test_feature_doc_scope_field(
        self,
        session: AsyncSession,
        feature: KFeature,
        doc: KDoc,
        creator_id: UUID,
    ):
        """Test that feature docs can have different org_ids."""
        from app.models import KOrganization

        # Create two organizations
        org1 = KOrganization(
            name="Organization 1",
            alias="org1_feature_doc_scope",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        org2 = KOrganization(
            name="Organization 2",
            alias="org2_feature_doc_scope",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add_all([org1, org2])
        await session.commit()
        await session.refresh(org1)
        await session.refresh(org2)

        feature_doc1 = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=org1.id,
            role="main",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc1)
        await session.commit()

        # Create another feature and doc and add with different org_id
        feature2 = KFeature(
            name="Another Feature",
            org_id=org2.id,
            feature_type=FeatureType.PRODUCT,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        doc2 = KDoc(
            name="Another Doc",
            org_id=org2.id,
            content="Content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(feature2)
        session.add(doc2)
        await session.commit()

        feature_doc2 = KFeatureDoc(
            feature_id=feature2.id,
            doc_id=doc2.id,
            org_id=org2.id,
            role="supplementary",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(feature_doc2)
        await session.commit()

        # Verify different org_ids
        result_exec = await session.execute(select(KFeatureDoc))
        relationships = result_exec.scalars().all()

        assert len(relationships) == 2
        org_ids = {r.org_id for r in relationships}
        assert org_ids == {org1.id, org2.id}

    @pytest.mark.asyncio
    async def test_feature_doc_count(
        self,
        session: AsyncSession,
        feature: KFeature,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test counting feature docs."""
        docs = []
        for i in range(5):
            doc = KDoc(
                name=f"Doc {i}",
                org_id=test_org_id,
                content=f"Content {i}",
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            docs.append(doc)
            session.add(doc)

        await session.commit()

        # Add all docs to the feature
        for doc in docs:
            feature_doc = KFeatureDoc(
                feature_id=feature.id,
                doc_id=doc.id,
                org_id=test_org_id,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(feature_doc)

        await session.commit()

        # Count docs
        result_exec = await session.execute(
            select(KFeatureDoc).where(KFeatureDoc.feature_id == feature.id)
        )
        feature_docs = result_exec.scalars().all()

        assert len(feature_docs) == 5
