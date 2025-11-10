"""Unit tests for feature doc management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KDoc, KFeature, KFeatureDoc
from app.models.k_feature import FeatureType
from app.routes.v1.feature_docs import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with feature_docs router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


@pytest.fixture
async def feature(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KFeature:
    """Create a test feature."""
    feature = KFeature(
        name="User Authentication Feature",
        org_id=test_org_id,
        feature_type=FeatureType.PRODUCT,
        summary="Feature for user authentication",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(feature)
    await async_session.commit()
    await async_session.refresh(feature)
    return feature


@pytest.fixture
async def doc(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KDoc:
    """Create a test doc."""
    doc = KDoc(
        name="Authentication Specification",
        org_id=test_org_id,
        content="This is the authentication specification document",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(doc)
    await async_session.commit()
    await async_session.refresh(doc)
    return doc


class TestAddFeatureDoc:
    """Test suite for POST /features/{feature_id}/docs endpoint."""

    async def test_add_feature_doc_success(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new doc to a feature."""
        doc_data = {
            "doc_id": str(doc.id),
            "role": "specification",
            "meta": {"version": "1.0", "status": "draft"},
        }

        response = await client.post(f"/features/{feature.id}/docs", json=doc_data)

        assert response.status_code == 201
        data = response.json()
        assert data["feature_id"] == str(feature.id)
        assert data["doc_id"] == str(doc.id)
        assert data["role"] == "specification"
        assert data["meta"] == {"version": "1.0", "status": "draft"}
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_add_feature_doc_minimal_data(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        test_org_id: UUID,
    ):
        """Test adding a feature doc with minimal required fields."""
        doc_data = {"doc_id": str(doc.id)}

        response = await client.post(f"/features/{feature.id}/docs", json=doc_data)

        assert response.status_code == 201
        data = response.json()
        assert data["feature_id"] == str(feature.id)
        assert data["doc_id"] == str(doc.id)
        assert data["role"] is None
        assert data["meta"] == {}

    async def test_add_feature_doc_duplicate(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test that adding a duplicate feature doc fails."""
        # Add feature doc directly in database
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()
        async_session.expunge(feature_doc)

        # Try to add same doc via API
        doc_data = {"doc_id": str(doc.id)}

        response = await client.post(f"/features/{feature.id}/docs", json=doc_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_add_feature_doc_feature_not_found(
        self,
        client: AsyncClient,
        doc: KDoc,
    ):
        """Test adding a doc to a non-existent feature."""
        non_existent_feature_id = uuid7()
        doc_data = {"doc_id": str(doc.id)}

        response = await client.post(
            f"/features/{non_existent_feature_id}/docs", json=doc_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_add_feature_doc_doc_not_found(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test adding a non-existent doc to a feature."""
        non_existent_doc_id = uuid7()
        doc_data = {"doc_id": str(non_existent_doc_id)}

        response = await client.post(f"/features/{feature.id}/docs", json=doc_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_add_feature_doc_with_role(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
    ):
        """Test adding a feature doc with a specific role."""
        doc_data = {"doc_id": str(doc.id), "role": "reference"}

        response = await client.post(f"/features/{feature.id}/docs", json=doc_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "reference"

    async def test_add_feature_doc_with_complex_meta(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
    ):
        """Test adding a feature doc with complex metadata."""
        doc_data = {
            "doc_id": str(doc.id),
            "role": "specification",
            "meta": {
                "tags": ["auth", "security", "oauth"],
                "reviewers": {"lead": "john.doe", "backup": "jane.smith"},
                "metrics": {"completeness": 0.85, "reviews": 3},
            },
        }

        response = await client.post(f"/features/{feature.id}/docs", json=doc_data)

        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == doc_data["meta"]


class TestListFeatureDocs:
    """Test suite for GET /features/{feature_id}/docs endpoint."""

    async def test_list_feature_docs_empty(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test listing feature docs when none exist."""
        response = await client.get(f"/features/{feature.id}/docs")

        assert response.status_code == 200
        data = response.json()
        assert data["docs"] == []

    async def test_list_feature_docs_single(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing feature docs with a single doc."""
        # Add a doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="specification",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        response = await client.get(f"/features/{feature.id}/docs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["docs"]) == 1
        assert data["docs"][0]["feature_id"] == str(feature.id)
        assert data["docs"][0]["doc_id"] == str(doc.id)
        assert data["docs"][0]["role"] == "specification"

    async def test_list_feature_docs_multiple(
        self,
        client: AsyncClient,
        feature: KFeature,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple feature docs."""
        # Create multiple docs and add to feature
        docs_data = [
            {"name": "Doc 1", "content": "Content 1", "role": "specification"},
            {"name": "Doc 2", "content": "Content 2", "role": "reference"},
            {"name": "Doc 3", "content": "Content 3", "role": "tutorial"},
        ]

        for d_data in docs_data:
            doc = KDoc(
                name=d_data["name"],
                org_id=test_org_id,
                content=d_data["content"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(doc)
            await async_session.commit()
            await async_session.refresh(doc)

            feature_doc = KFeatureDoc(
                feature_id=feature.id,
                doc_id=doc.id,
                org_id=test_org_id,
                role=d_data["role"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(feature_doc)

        await async_session.commit()

        response = await client.get(f"/features/{feature.id}/docs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["docs"]) == 3
        roles = {d["role"] for d in data["docs"]}
        assert roles == {"specification", "reference", "tutorial"}

    async def test_list_feature_docs_feature_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing docs of a non-existent feature."""
        non_existent_feature_id = uuid7()

        response = await client.get(f"/features/{non_existent_feature_id}/docs")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetFeatureDoc:
    """Test suite for GET /features/{feature_id}/docs/{doc_id} endpoint."""

    async def test_get_feature_doc_success(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully getting a single feature doc."""
        # Add feature doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="specification",
            meta={"version": "2.0"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        response = await client.get(f"/features/{feature.id}/docs/{doc.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["feature_id"] == str(feature.id)
        assert data["doc_id"] == str(doc.id)
        assert data["role"] == "specification"
        assert data["meta"] == {"version": "2.0"}

    async def test_get_feature_doc_not_found(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test getting a feature doc that doesn't exist."""
        non_existent_doc_id = uuid7()

        response = await client.get(
            f"/features/{feature.id}/docs/{non_existent_doc_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateFeatureDoc:
    """Test suite for PATCH /features/{feature_id}/docs/{doc_id} endpoint."""

    async def test_update_feature_doc_role(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating a feature doc's role."""
        # Add feature doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="draft",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        update_data = {"role": "final"}

        response = await client.patch(
            f"/features/{feature.id}/docs/{doc.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "final"
        assert data["feature_id"] == str(feature.id)
        assert data["doc_id"] == str(doc.id)

    async def test_update_feature_doc_meta(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating a feature doc's metadata."""
        # Add feature doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        update_data = {"meta": {"new": "data", "updated": True}}

        response = await client.patch(
            f"/features/{feature.id}/docs/{doc.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}

    async def test_update_feature_doc_both_fields(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating both role and meta."""
        # Add feature doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="draft",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        update_data = {"role": "approved_specification", "meta": {"new": "data"}}

        response = await client.patch(
            f"/features/{feature.id}/docs/{doc.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "approved_specification"
        assert data["meta"] == {"new": "data"}

    async def test_update_feature_doc_not_found(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test updating a feature doc that doesn't exist."""
        non_existent_doc_id = uuid7()
        update_data = {"role": "final"}

        response = await client.patch(
            f"/features/{feature.id}/docs/{non_existent_doc_id}", json=update_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_update_feature_doc_empty_payload(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Add feature doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            role="specification",
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        update_data = {}

        response = await client.patch(
            f"/features/{feature.id}/docs/{doc.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "specification"
        assert data["meta"] == {"key": "value"}


class TestRemoveFeatureDoc:
    """Test suite for DELETE /features/{feature_id}/docs/{doc_id} endpoint."""

    async def test_remove_feature_doc_success(
        self,
        client: AsyncClient,
        feature: KFeature,
        doc: KDoc,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a feature doc."""
        # Add feature doc
        feature_doc = KFeatureDoc(
            feature_id=feature.id,
            doc_id=doc.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature_doc)
        await async_session.commit()

        response = await client.delete(f"/features/{feature.id}/docs/{doc.id}")

        assert response.status_code == 204
        assert response.content == b""

        # Verify feature doc is soft-deleted
        from sqlmodel import select

        result = await async_session.execute(
            select(KFeatureDoc).where(
                KFeatureDoc.feature_id == feature.id,
                KFeatureDoc.doc_id == doc.id,
            )
        )
        deleted_feature_doc = result.scalar_one_or_none()
        assert deleted_feature_doc is not None
        assert deleted_feature_doc.deleted_at is not None

    async def test_remove_feature_doc_not_found(
        self,
        client: AsyncClient,
        feature: KFeature,
    ):
        """Test removing a feature doc that doesn't exist."""
        non_existent_doc_id = uuid7()

        response = await client.delete(
            f"/features/{feature.id}/docs/{non_existent_doc_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
