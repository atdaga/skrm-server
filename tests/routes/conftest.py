"""Shared fixtures for versioned and non-versioned API route tests."""

from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KPrincipal
from app.schemas.user import TokenData


@pytest.fixture
def app() -> FastAPI:
    """Create a basic FastAPI app for testing.

    This fixture provides a clean FastAPI instance without any routes.
    Individual test files should include their specific router.
    """
    return FastAPI()


@pytest.fixture
def app_with_overrides(
    async_session: AsyncSession, mock_token_data: TokenData, mock_user
) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing.

    This fixture provides a base FastAPI app with database and token
    authentication dependencies overridden for testing. Individual test
    files should include their specific router.

    This is used by v1, v2, and other versioned API tests.
    """
    app = FastAPI()

    # Override dependencies
    async def override_get_db():
        yield async_session

    async def override_oauth2_scheme():
        return "test-token"

    async def override_get_current_token():
        return mock_token_data

    async def override_get_current_user():
        return mock_user

    from app.core.auth import oauth2_scheme
    from app.core.db.database import get_db
    from app.routes.deps import get_current_token, get_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme
    app.dependency_overrides[get_current_token] = override_get_current_token
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing.

    This fixture creates an async HTTP client configured to work with
    the app fixture. For authenticated API routes (v1, v2), this fixture
    should be overridden in the versioned conftest to use app_with_overrides.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def app_without_auth() -> FastAPI:
    """Create a FastAPI app without authentication overrides.

    This is useful for testing endpoints that should reject unauthenticated
    requests.
    """
    return FastAPI()


@pytest.fixture
async def client_no_auth(app_without_auth: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing without authentication.

    This fixture creates a client that doesn't have authentication
    dependencies overridden, useful for testing auth failures.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_without_auth), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def principal(async_session: AsyncSession, test_user_id: UUID) -> KPrincipal:
    """Create a test principal (user) for testing.

    This creates a separate principal that can be added to organizations,
    teams, etc. Useful for testing member management in v1/v2 APIs.
    """
    principal = KPrincipal(
        username="testprincipal",
        primary_email="principal@example.com",
        first_name="Test",
        last_name="Principal",
        display_name="Test Principal",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()
    await async_session.refresh(principal)
    return principal
