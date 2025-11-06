"""Unit tests for doc management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KDoc, KOrganization
from app.routes.deps import get_current_token
from app.routes.v1.docs import router
from app.schemas.user import TokenData
from tests.conftest import add_user_to_organization


@pytest.fixture
def app_with_overrides(
    async_session: AsyncSession, mock_token_data: TokenData
) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    async def override_get_db():
        yield async_session

    async def override_get_current_token():
        return mock_token_data

    from app.core.db.database import get_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_token] = override_get_current_token

    return app


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def test_organization(
    async_session: AsyncSession, test_user_id: UUID
) -> KOrganization:
    """Create a test organization with the test user as a member."""
    organization = KOrganization(
        name="Test Organization",
        alias="test_org",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(organization)
    await async_session.commit()
    await async_session.refresh(organization)

    # Add test user as organization principal
    await add_user_to_organization(async_session, organization.id, test_user_id)

    return organization


class TestCreateDoc:
    """Test suite for POST /docs endpoint."""

    @pytest.mark.asyncio
    async def test_create_doc_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
        test_scope: str,
    ):
        """Test successfully creating a new doc."""
        doc_data = {
            "name": "API Documentation",
            "description": "REST API documentation",
            "content": "# API Documentation\n\nThis is the API documentation content.",
            "meta": {"version": "1.0", "status": "draft"},
        }

        response = await client.post(
            f"/documents?org_id={test_organization.id}", json=doc_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Documentation"
        assert data["description"] == "REST API documentation"
        assert (
            data["content"]
            == "# API Documentation\n\nThis is the API documentation content."
        )
        assert data["meta"] == {"version": "1.0", "status": "draft"}
        assert "id" in data
        assert UUID(data["id"])  # Validates it's a proper UUID
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_create_doc_minimal_fields(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        test_user_id: UUID,
    ):
        """Test creating a doc with only required fields."""
        doc_data = {"name": "Quick Notes", "content": "Some quick notes here."}

        response = await client.post(
            f"/documents?org_id={test_organization.id}", json=doc_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Quick Notes"
        assert data["description"] is None
        assert data["content"] == "Some quick notes here."
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_create_doc_duplicate_name(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test that creating a doc with duplicate name fails."""
        doc_data = {"name": "User Guide", "content": "First version"}

        # Create first doc
        response = await client.post(
            f"/documents?org_id={test_organization.id}", json=doc_data
        )
        assert response.status_code == 201

        # Try to create second doc with same name
        doc_data["content"] = "Second version"
        response = await client.post(
            f"/documents?org_id={test_organization.id}", json=doc_data
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_doc_unauthorized_org(
        self, client: AsyncClient, test_user_id: UUID
    ):
        """Test that creating a doc in unauthorized org fails."""
        unauthorized_org_id = uuid4()
        doc_data = {"name": "Test Doc", "content": "Test content"}

        response = await client.post(
            f"/documents?org_id={unauthorized_org_id}", json=doc_data
        )
        assert response.status_code == 403


class TestListDocs:
    """Test suite for GET /docs endpoint."""

    @pytest.mark.asyncio
    async def test_list_docs_empty(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test listing docs when none exist."""
        response = await client.get(f"/documents?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["docs"] == []

    @pytest.mark.asyncio
    async def test_list_docs_multiple(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test listing multiple docs."""
        # Create multiple docs
        docs = [
            KDoc(
                name="Doc Alpha",
                content="Alpha content",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
            KDoc(
                name="Doc Beta",
                description="Beta doc",
                content="Beta content",
                org_id=test_organization.id,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            ),
        ]

        for doc in docs:
            async_session.add(doc)
        await async_session.commit()

        response = await client.get(f"/documents?org_id={test_organization.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["docs"]) == 2
        doc_names = [d["name"] for d in data["docs"]]
        assert "Doc Alpha" in doc_names
        assert "Doc Beta" in doc_names

    @pytest.mark.asyncio
    async def test_list_docs_unauthorized_org(self, client: AsyncClient):
        """Test that listing docs in unauthorized org fails."""
        unauthorized_org_id = uuid4()

        response = await client.get(f"/documents?org_id={unauthorized_org_id}")
        assert response.status_code == 403


class TestGetDoc:
    """Test suite for GET /docs/{doc_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_doc_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully retrieving a doc."""
        doc = KDoc(
            name="Architecture Doc",
            description="System architecture",
            content="# Architecture\n\nDetailed architecture documentation.",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        response = await client.get(
            f"/documents/{doc.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(doc.id)
        assert data["name"] == "Architecture Doc"
        assert data["description"] == "System architecture"
        assert (
            data["content"] == "# Architecture\n\nDetailed architecture documentation."
        )

    @pytest.mark.asyncio
    async def test_get_doc_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test getting a non-existent doc."""
        non_existent_id = uuid4()

        response = await client.get(
            f"/documents/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_doc_wrong_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test getting a doc with wrong org_id."""
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        doc = KDoc(
            name="Secret Doc",
            content="Secret content",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        # Try to access with unauthorized org
        wrong_org_id = uuid4()
        response = await client.get(f"/documents/{doc.id}?org_id={wrong_org_id}")
        assert response.status_code == 403


class TestUpdateDoc:
    """Test suite for PATCH /docs/{doc_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_doc_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully updating a doc."""
        doc = KDoc(
            name="Old Name",
            description="Old description",
            content="Old content",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        update_data = {
            "name": "New Name",
            "description": "New description",
            "content": "New content",
            "meta": {"status": "updated"},
        }

        response = await client.patch(
            f"/documents/{doc.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"
        assert data["content"] == "New content"
        assert data["meta"] == {"status": "updated"}

    @pytest.mark.asyncio
    async def test_update_doc_partial(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test updating only some fields of a doc."""
        doc = KDoc(
            name="Original Doc",
            description="Original description",
            content="Original content",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        update_data = {"content": "Updated content"}

        response = await client.patch(
            f"/documents/{doc.id}?org_id={test_organization.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original Doc"  # Unchanged
        assert data["description"] == "Original description"  # Unchanged
        assert data["content"] == "Updated content"  # Changed

    @pytest.mark.asyncio
    async def test_update_doc_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test updating a non-existent doc."""
        non_existent_id = uuid4()
        update_data = {"name": "New Name"}

        response = await client.patch(
            f"/documents/{non_existent_id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_doc_duplicate_name(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating to a duplicate name fails."""
        doc1 = KDoc(
            name="Doc One",
            content="Content one",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        doc2 = KDoc(
            name="Doc Two",
            content="Content two",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )

        async_session.add_all([doc1, doc2])
        await async_session.commit()
        await async_session.refresh(doc2)

        # Try to update doc2 to have the same name as doc1
        update_data = {"name": "Doc One"}
        response = await client.patch(
            f"/documents/{doc2.id}?org_id={test_organization.id}",
            json=update_data,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_doc_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that updating a doc in unauthorized org fails."""
        # Create a doc in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        doc = KDoc(
            name="Other Doc",
            content="Other content",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        # Try to update with unauthorized org (user is not member of other_org)
        update_data = {"name": "Updated Name"}
        response = await client.patch(
            f"/documents/{doc.id}?org_id={other_org.id}",
            json=update_data,
        )
        assert response.status_code == 403


class TestDeleteDoc:
    """Test suite for DELETE /docs/{doc_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_doc_success(
        self,
        client: AsyncClient,
        test_organization: KOrganization,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test successfully deleting a doc."""
        doc = KDoc(
            name="To Delete",
            content="Content to delete",
            org_id=test_organization.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        response = await client.delete(
            f"/documents/{doc.id}?org_id={test_organization.id}"
        )

        assert response.status_code == 204

        # Verify doc is deleted
        get_response = await client.get(f"/docs/{doc.id}?org_id={test_organization.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_doc_not_found(
        self, client: AsyncClient, test_organization: KOrganization
    ):
        """Test deleting a non-existent doc."""
        non_existent_id = uuid4()

        response = await client.delete(
            f"/documents/{non_existent_id}?org_id={test_organization.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_doc_unauthorized_org(
        self,
        client: AsyncClient,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that deleting a doc in unauthorized org fails."""
        # Create a doc in a different org
        other_org = KOrganization(
            name="Other Org",
            alias="other_org",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_org)
        await async_session.commit()
        await async_session.refresh(other_org)

        doc = KDoc(
            name="Other Doc",
            content="Other content",
            org_id=other_org.id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(doc)
        await async_session.commit()
        await async_session.refresh(doc)

        # Try to delete with unauthorized org (user is not member of other_org)
        response = await client.delete(f"/documents/{doc.id}?org_id={other_org.id}")
        assert response.status_code == 403
