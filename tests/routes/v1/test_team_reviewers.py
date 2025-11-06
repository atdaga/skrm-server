"""Unit tests for team reviewer management endpoints."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KPrincipal, KTeam, KTeamReviewer
from app.routes.deps import get_current_token
from app.routes.v1.team_reviewers import router
from app.schemas.user import TokenData


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
async def team(
    async_session: AsyncSession, test_org_id: UUID, test_user_id: UUID
) -> KTeam:
    """Create a test team."""
    team = KTeam(
        name="Engineering Team",
        org_id=test_org_id,
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(team)
    await async_session.commit()
    await async_session.refresh(team)
    return team


@pytest.fixture
async def principal(async_session: AsyncSession, test_user_id: UUID) -> KPrincipal:
    """Create a test principal."""
    principal = KPrincipal(
        username="testreviewer",
        primary_email="reviewer@example.com",
        first_name="Test",
        last_name="Reviewer",
        display_name="Test Reviewer",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()
    await async_session.refresh(principal)
    return principal


class TestAddTeamReviewer:
    """Test suite for POST /teams/{team_id}/reviewers endpoint."""

    @pytest.mark.asyncio
    async def test_add_team_reviewer_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully adding a new team reviewer."""
        reviewer_data = {
            "principal_id": str(principal.id),
            "role": "lead_reviewer",
            "meta": {"specialization": "security", "experience_years": 5},
        }

        response = await client.post(f"/teams/{team.id}/reviewers", json=reviewer_data)

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "lead_reviewer"
        assert data["meta"] == {"specialization": "security", "experience_years": 5}
        assert data["created_by"] == str(test_user_id)
        assert data["last_modified_by"] == str(test_user_id)
        assert "created" in data
        assert "last_modified" in data

    @pytest.mark.asyncio
    async def test_add_team_reviewer_minimal_data(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        test_org_id: UUID,
    ):
        """Test adding a team reviewer with minimal required fields."""
        reviewer_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/teams/{team.id}/reviewers", json=reviewer_data)

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] is None
        assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_add_team_reviewer_duplicate(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test that adding a duplicate team reviewer fails."""
        # Add reviewer directly in database
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()
        async_session.expunge(reviewer)

        # Try to add same reviewer via API
        reviewer_data = {"principal_id": str(principal.id)}

        response = await client.post(f"/teams/{team.id}/reviewers", json=reviewer_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_team_reviewer_team_not_found(
        self,
        client: AsyncClient,
        principal: KPrincipal,
    ):
        """Test adding a reviewer to a non-existent team."""
        non_existent_team_id = uuid4()
        reviewer_data = {"principal_id": str(principal.id)}

        response = await client.post(
            f"/teams/{non_existent_team_id}/reviewers", json=reviewer_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_team_reviewer_with_role(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
    ):
        """Test adding a team reviewer with a specific role."""
        reviewer_data = {"principal_id": str(principal.id), "role": "senior_reviewer"}

        response = await client.post(f"/teams/{team.id}/reviewers", json=reviewer_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "senior_reviewer"

    @pytest.mark.asyncio
    async def test_add_team_reviewer_with_complex_meta(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
    ):
        """Test adding a team reviewer with complex metadata."""
        reviewer_data = {
            "principal_id": str(principal.id),
            "role": "lead_reviewer",
            "meta": {
                "specializations": ["security", "performance", "architecture"],
                "certifications": {"cissp": True, "ceh": True},
                "stats": {"reviews_completed": 250, "avg_rating": 4.8},
            },
        }

        response = await client.post(f"/teams/{team.id}/reviewers", json=reviewer_data)

        assert response.status_code == 201
        data = response.json()
        assert data["meta"] == reviewer_data["meta"]


class TestListTeamReviewers:
    """Test suite for GET /teams/{team_id}/reviewers endpoint."""

    @pytest.mark.asyncio
    async def test_list_team_reviewers_empty(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test listing team reviewers when none exist."""
        response = await client.get(f"/teams/{team.id}/reviewers")

        assert response.status_code == 200
        data = response.json()
        assert data["reviewers"] == []

    @pytest.mark.asyncio
    async def test_list_team_reviewers_single(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing team reviewers with a single reviewer."""
        # Add a reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead_reviewer",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/reviewers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["reviewers"]) == 1
        assert data["reviewers"][0]["team_id"] == str(team.id)
        assert data["reviewers"][0]["principal_id"] == str(principal.id)
        assert data["reviewers"][0]["role"] == "lead_reviewer"

    @pytest.mark.asyncio
    async def test_list_team_reviewers_multiple(
        self,
        client: AsyncClient,
        team: KTeam,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test listing multiple team reviewers."""
        # Create multiple principals and add as reviewers
        reviewers_data = [
            {
                "username": "reviewer1",
                "email": "reviewer1@example.com",
                "role": "lead_reviewer",
            },
            {
                "username": "reviewer2",
                "email": "reviewer2@example.com",
                "role": "senior_reviewer",
            },
            {
                "username": "reviewer3",
                "email": "reviewer3@example.com",
                "role": "reviewer",
            },
        ]

        for idx, r_data in enumerate(reviewers_data):
            principal = KPrincipal(
                username=r_data["username"],
                primary_email=r_data["email"],
                first_name="Reviewer",
                last_name=str(idx),
                display_name=f"Reviewer {idx}",
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(principal)
            await async_session.commit()
            await async_session.refresh(principal)

            reviewer = KTeamReviewer(
                team_id=team.id,
                principal_id=principal.id,
                org_id=test_org_id,
                role=r_data["role"],
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(reviewer)

        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/reviewers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["reviewers"]) == 3
        roles = {r["role"] for r in data["reviewers"]}
        assert roles == {"lead_reviewer", "senior_reviewer", "reviewer"}

    @pytest.mark.asyncio
    async def test_list_team_reviewers_team_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing reviewers of a non-existent team."""
        non_existent_team_id = uuid4()

        response = await client.get(f"/teams/{non_existent_team_id}/reviewers")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetTeamReviewer:
    """Test suite for GET /teams/{team_id}/reviewers/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_team_reviewer_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully getting a single team reviewer."""
        # Add reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead_reviewer",
            meta={"specialization": "security"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        response = await client.get(f"/teams/{team.id}/reviewers/{principal.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)
        assert data["role"] == "lead_reviewer"
        assert data["meta"] == {"specialization": "security"}

    @pytest.mark.asyncio
    async def test_get_team_reviewer_not_found(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test getting a team reviewer that doesn't exist."""
        non_existent_principal_id = uuid4()

        response = await client.get(
            f"/teams/{team.id}/reviewers/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestUpdateTeamReviewer:
    """Test suite for PATCH /teams/{team_id}/reviewers/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_team_reviewer_role(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating a team reviewer's role."""
        # Add reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="reviewer",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        update_data = {"role": "lead_reviewer"}

        response = await client.patch(
            f"/teams/{team.id}/reviewers/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "lead_reviewer"
        assert data["team_id"] == str(team.id)
        assert data["principal_id"] == str(principal.id)

    @pytest.mark.asyncio
    async def test_update_team_reviewer_meta(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating a team reviewer's metadata."""
        # Add reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        update_data = {"meta": {"new": "data", "updated": True}}

        response = await client.patch(
            f"/teams/{team.id}/reviewers/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"] == {"new": "data", "updated": True}

    @pytest.mark.asyncio
    async def test_update_team_reviewer_both_fields(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating both role and meta."""
        # Add reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="reviewer",
            meta={"old": "data"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        update_data = {"role": "senior_reviewer", "meta": {"new": "data"}}

        response = await client.patch(
            f"/teams/{team.id}/reviewers/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "senior_reviewer"
        assert data["meta"] == {"new": "data"}

    @pytest.mark.asyncio
    async def test_update_team_reviewer_not_found(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test updating a team reviewer that doesn't exist."""
        non_existent_principal_id = uuid4()
        update_data = {"role": "lead_reviewer"}

        response = await client.patch(
            f"/teams/{team.id}/reviewers/{non_existent_principal_id}", json=update_data
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_team_reviewer_empty_payload(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test updating with empty payload (no changes)."""
        # Add reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead_reviewer",
            meta={"key": "value"},
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        update_data = {}

        response = await client.patch(
            f"/teams/{team.id}/reviewers/{principal.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "lead_reviewer"
        assert data["meta"] == {"key": "value"}


class TestRemoveTeamReviewer:
    """Test suite for DELETE /teams/{team_id}/reviewers/{principal_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_team_reviewer_success(
        self,
        client: AsyncClient,
        team: KTeam,
        principal: KPrincipal,
        async_session: AsyncSession,
        test_org_id: UUID,
        test_user_id: UUID,
    ):
        """Test successfully removing a team reviewer."""
        # Add reviewer
        reviewer = KTeamReviewer(
            team_id=team.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(reviewer)
        await async_session.commit()

        response = await client.delete(f"/teams/{team.id}/reviewers/{principal.id}")

        assert response.status_code == 204
        assert response.content == b""

        # Verify reviewer is actually deleted
        from sqlmodel import select

        result = await async_session.execute(
            select(KTeamReviewer).where(
                KTeamReviewer.team_id == team.id,
                KTeamReviewer.principal_id == principal.id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_team_reviewer_not_found(
        self,
        client: AsyncClient,
        team: KTeam,
    ):
        """Test removing a team reviewer that doesn't exist."""
        non_existent_principal_id = uuid4()

        response = await client.delete(
            f"/teams/{team.id}/reviewers/{non_existent_principal_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
