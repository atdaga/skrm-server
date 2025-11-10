"""V1 API-specific test configuration.

This conftest overrides fixtures from the parent routes/conftest.py
to use authenticated app configurations for v1 API testing.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Override client fixture to use app_with_overrides for v1 API tests.

    This ensures v1 tests use the authenticated app with database and
    token dependency overrides.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def app_with_root_user_overrides(
    async_session: AsyncSession, mock_token_data, mock_system_root_user
):
    """Create a FastAPI app with system root user overrides for hard delete testing.

    This fixture provides an app configured with a system root user who has
    privileges to perform hard deletes.
    """
    from app.core.auth import oauth2_scheme
    from app.core.db.database import get_db
    from app.routes.deps import get_current_token, get_current_user

    app = FastAPI()

    async def override_get_db():
        yield async_session

    async def override_oauth2_scheme():
        return "test-token"

    async def override_get_current_token():
        return mock_token_data

    async def override_get_current_user():
        return mock_system_root_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme
    app.dependency_overrides[get_current_token] = override_get_current_token
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
async def root_client(app_with_root_user_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing with system root user privileges.

    This client can be used to test hard delete operations that require
    elevated privileges.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_with_root_user_overrides),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def app_with_system_user_overrides(
    async_session: AsyncSession, mock_token_data, mock_system_user
):
    """Create a FastAPI app with system user overrides.

    This fixture provides an app configured with a SYSTEM role user who can
    perform user CUD operations.
    """
    from app.core.auth import oauth2_scheme
    from app.core.db.database import get_db
    from app.routes.deps import get_current_token, get_current_user

    app = FastAPI()

    async def override_get_db():
        yield async_session

    async def override_oauth2_scheme():
        return "test-token"

    async def override_get_current_token():
        return mock_token_data

    async def override_get_current_user():
        return mock_system_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme
    app.dependency_overrides[get_current_token] = override_get_current_token
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
async def system_client(app_with_system_user_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing with system user privileges.

    This client can be used to test user CUD operations.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_with_system_user_overrides),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def app_with_system_admin_user_overrides(
    async_session: AsyncSession, mock_token_data, mock_system_admin_user
):
    """Create a FastAPI app with system admin user overrides.

    This fixture provides an app configured with a SYSTEM_ADMIN role user who can
    perform organization and organization_principal CUD operations.
    """
    from app.core.auth import oauth2_scheme
    from app.core.db.database import get_db
    from app.routes.deps import get_current_token, get_current_user

    app = FastAPI()

    async def override_get_db():
        yield async_session

    async def override_oauth2_scheme():
        return "test-token"

    async def override_get_current_token():
        return mock_token_data

    async def override_get_current_user():
        return mock_system_admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[oauth2_scheme] = override_oauth2_scheme
    app.dependency_overrides[get_current_token] = override_get_current_token
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
async def admin_client(app_with_system_admin_user_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing with system admin user privileges.

    This client can be used to test organization and organization_principal CUD operations.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_with_system_admin_user_overrides),
        base_url="http://test",
    ) as ac:
        yield ac
