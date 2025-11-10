"""Unit tests for feature management endpoints."""

from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KFeature, KOrganization
from app.models.k_feature import FeatureType
from app.routes.v1.features import router


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with features router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestCreateFeature:
    """Test suite for POST /features endpoint."""

    async def test_create_feature_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test successfully creating a new feature."""
        feature_data = {
            "name": "User Authentication",
            "feature_type": "Product",
            "summary": "Implement user authentication system",
            "notes": "Use OAuth 2.0",
            "guestimate": 5.0,
            "meta": {"priority": "high"},
        }

        response = await client.post(
            f"/features?org_id={test_organization.id}", json=feature_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "User Authentication"
        assert data["feature_type"] == "Product"
        assert data["summary"] == "Implement user authentication system"
        assert data["notes"] == "Use OAuth 2.0"
        assert data["guestimate"] == 5.0
        assert data["review_result"] is None
        assert data["meta"] == {"priority": "high"}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    async def test_create_feature_minimal_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
    ):
        """Test creating a feature with only required fields."""
        feature_data = {"name": "Dashboard UI", "feature_type": "Product"}

        response = await client.post(
            f"/features?org_id={test_organization.id}", json=feature_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dashboard UI"
        assert data["feature_type"] == "Product"
        assert data["parent"] is None
        assert data["parent_path"] is None
        assert data["summary"] is None
        assert data["notes"] is None
        assert data["guestimate"] is None
        assert data["derived_guestimate"] is None
        assert data["review_result"] is None
        assert data["meta"] == {}

    async def test_create_feature_with_parent(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test creating a feature with a parent reference."""
        # Create parent feature
        parent_feature = KFeature(
            org_id=test_organization.id,
            name="Parent Feature",
            feature_type=FeatureType.PRODUCT,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(parent_feature)
        await async_session.commit()
        await async_session.refresh(parent_feature)

        feature_data = {
            "name": "Child Feature",
            "feature_type": "Engineering",
            "parent": str(parent_feature.id),
            "parent_path": "/Parent Feature",
        }

        response = await client.post(
            f"/features?org_id={test_organization.id}", json=feature_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["parent"] == str(parent_feature.id)
        assert data["parent_path"] == "/Parent Feature"

    async def test_create_feature_duplicate_name(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test that creating a feature with duplicate name fails."""
        feature_data = {"name": "Duplicate Feature", "feature_type": "Product"}

        # Create first feature
        response = await client.post(
            f"/features?org_id={test_organization.id}", json=feature_data
        )
        assert response.status_code == 201

        # Try to create second feature with same name
        response = await client.post(
            f"/features?org_id={test_organization.id}", json=feature_data
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_create_feature_unauthorized_org(self, client: AsyncClient):
        """Test that creating a feature in unauthorized org fails."""
        unauthorized_org_id = uuid7()
        feature_data = {"name": "Test Feature", "feature_type": "Product"}

        response = await client.post(
            f"/features?org_id={unauthorized_org_id}", json=feature_data
        )
        assert response.status_code == 403


class TestListFeatures:
    """Test suite for GET /features endpoint."""

    async def test_list_features_empty(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test listing features when none exist."""
        response = await client.get(f"/features?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["features"] == []

    async def test_list_features_multiple(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple features."""
        # Create multiple features
        features = [
            KFeature(
                name="Feature 1",
                feature_type=FeatureType.PRODUCT,
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
            KFeature(
                name="Feature 2",
                feature_type=FeatureType.ENGINEERING,
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
        ]

        for feature in features:
            async_session.add(feature)
        await async_session.commit()

        response = await client.get(f"/features?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["features"]) == 2
        feature_names = [f["name"] for f in data["features"]]
        assert "Feature 1" in feature_names
        assert "Feature 2" in feature_names

    async def test_list_features_unauthorized_org(self, client: AsyncClient):
        """Test that listing features in unauthorized org fails."""
        unauthorized_org_id = uuid7()

        response = await client.get(f"/features?org_id={unauthorized_org_id}")
        assert response.status_code == 403


class TestGetFeature:
    """Test suite for GET /features/{feature_id} endpoint."""

    async def test_get_feature_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a feature."""
        feature = KFeature(
            name="Test Feature",
            feature_type=FeatureType.PRODUCT,
            summary="Test summary",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        response = await client.get(
            f"/features/{feature.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(feature.id)
        assert data["name"] == "Test Feature"
        assert data["summary"] == "Test summary"

    async def test_get_feature_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test getting a non-existent feature."""
        non_existent_id = uuid7()

        response = await client.get(
            f"/features/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    async def test_get_feature_wrong_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a feature with wrong org_id."""
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        feature = KFeature(
            name="Secret Feature",
            feature_type=FeatureType.PRODUCT,
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        # Try to access with unauthorized org
        wrong_org_id = uuid7()
        response = await client.get(f"/features/{feature.id}?org_id={wrong_org_id}")
        assert response.status_code == 403


class TestUpdateFeature:
    """Test suite for PATCH /features/{feature_id} endpoint."""

    async def test_update_feature_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully updating a feature."""
        feature = KFeature(
            name="Old Name",
            feature_type=FeatureType.PRODUCT,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        update_data = {
            "name": "New Name",
            "summary": "Updated summary",
            "review_result": "Passed",
            "meta": {"priority": "medium"},
        }

        response = await client.patch(
            f"/features/{feature.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["summary"] == "Updated summary"
        assert data["review_result"] == "Passed"
        assert data["meta"] == {"priority": "medium"}

    async def test_update_feature_partial(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a feature."""
        feature = KFeature(
            name="Original Feature",
            feature_type=FeatureType.PRODUCT,
            summary="Original summary",
            guestimate=3.0,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        update_data = {"guestimate": 5.0}

        response = await client.patch(
            f"/features/{feature.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original Feature"  # Unchanged
        assert data["summary"] == "Original summary"  # Unchanged
        assert data["guestimate"] == 5.0  # Changed

    async def test_update_feature_all_optional_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating all optional fields including parent, parent_path, feature_type, notes, and derived_guestimate."""
        # Create parent features
        parent1 = KFeature(
            name="Parent Feature 1",
            feature_type=FeatureType.PRODUCT,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        parent2 = KFeature(
            name="Parent Feature 2",
            feature_type=FeatureType.PRODUCT,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add_all([parent1, parent2])
        await async_session.commit()
        await async_session.refresh(parent1)
        await async_session.refresh(parent2)

        # Create a feature with initial values
        feature = KFeature(
            name="Child Feature",
            feature_type=FeatureType.PRODUCT,
            parent=parent1.id,
            parent_path="/Parent Feature 1",
            summary="Initial summary",
            notes="Initial notes",
            guestimate=3.0,
            derived_guestimate=3.5,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        # Update all optional fields
        update_data = {
            "parent": str(parent2.id),
            "parent_path": "/Parent Feature 2",
            "feature_type": "Engineering",
            "notes": "Updated notes with more details",
            "derived_guestimate": 7.5,
        }

        response = await client.patch(
            f"/features/{feature.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["parent"] == str(parent2.id)
        assert data["parent_path"] == "/Parent Feature 2"
        assert data["feature_type"] == "Engineering"
        assert data["notes"] == "Updated notes with more details"
        assert data["derived_guestimate"] == 7.5
        # Verify unchanged fields
        assert data["name"] == "Child Feature"
        assert data["summary"] == "Initial summary"
        assert data["guestimate"] == 3.0

    async def test_update_feature_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test updating a non-existent feature."""
        non_existent_id = uuid7()
        update_data = {"name": "New Name"}

        response = await client.patch(
            f"/features/{non_existent_id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 404

    async def test_update_feature_duplicate_name(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating to a duplicate name fails."""
        feature1 = KFeature(
            name="Feature One",
            feature_type=FeatureType.PRODUCT,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        feature2 = KFeature(
            name="Feature Two",
            feature_type=FeatureType.PRODUCT,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )

        async_session.add_all([feature1, feature2])
        await async_session.commit()
        await async_session.refresh(feature2)

        # Try to update feature2 to have the same name as feature1
        update_data = {"name": "Feature One"}
        response = await client.patch(
            f"/features/{feature2.id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 409

    async def test_update_feature_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a feature in unauthorized org fails."""
        # Create a feature in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        feature = KFeature(
            name="Other Feature",
            feature_type=FeatureType.PRODUCT,
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        # Try to update with unauthorized org (user is not member of other_org)
        update_data = {"name": "Updated Name"}
        response = await client.patch(
            f"/features/{feature.id}?org_id={other_org.id}",
            json=update_data,
        )
        assert response.status_code == 403


class TestDeleteFeature:
    """Test suite for DELETE /features/{feature_id} endpoint."""

    async def test_delete_feature_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting a feature."""
        feature = KFeature(
            name="To Delete",
            feature_type=FeatureType.PRODUCT,
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        response = await client.delete(
            f"/features/{feature.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204

        # Verify feature is deleted
        get_response = await client.get(
            f"/features/{feature.id}?org_id={test_organization.id}"
        )
        assert get_response.status_code == 404

    async def test_delete_feature_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test deleting a non-existent feature."""
        non_existent_id = uuid7()

        response = await client.delete(
            f"/features/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    async def test_delete_feature_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a feature in unauthorized org fails."""
        # Create a feature in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        feature = KFeature(
            name="Other Feature",
            feature_type=FeatureType.PRODUCT,
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(feature)
        await async_session.commit()
        await async_session.refresh(feature)

        # Try to delete with unauthorized org (user is not member of other_org)
        response = await client.delete(f"/features/{feature.id}?org_id={other_org.id}")
        assert response.status_code == 403
