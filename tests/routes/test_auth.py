"""Unit tests for authentication endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.auth import router
from app.schemas.user import UserDetail


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with auth router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_user() -> UserDetail:
    """Create a mock user for testing."""
    user_id = uuid4()
    now = datetime.now()
    return UserDetail(
        id=user_id,
        scope="global",
        username="testuser",
        primary_email="test@example.com",
        primary_email_verified=True,
        primary_phone=None,
        primary_phone_verified=False,
        enabled=True,
        time_zone="UTC",
        name_prefix=None,
        first_name="Test",
        middle_name=None,
        last_name="User",
        name_suffix=None,
        display_name="Test User",
        default_locale="en",
        system_role="system_user",
        meta={},
        created=now,
        created_by=user_id,
        last_modified=now,
        last_modified_by=user_id,
    )


class TestLoginEndpoint:
    """Test suite for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, mock_user: UserDetail):
        """Test successful login with valid credentials."""
        with patch('app.routes.auth.authenticate_user', new_callable=AsyncMock) as mock_auth, \
             patch('app.routes.auth.create_access_token', new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_access_token_12345"
            
            response = await client.post(
                "/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test_access_token_12345"
            assert data["token_type"] == "bearer"
            
            # Verify authenticate_user was called with correct params
            mock_auth.assert_called_once_with("testuser", "testpassword")
            
            # Verify create_access_token was called
            mock_token.assert_called_once()
            call_args = mock_token.call_args[1]
            assert call_args["data"]["sub"] == str(mock_user.id)
            assert call_args["data"]["scope"] == "global"

    @pytest.mark.asyncio
    async def test_login_with_custom_scopes(self, client: AsyncClient, mock_user: UserDetail):
        """Test login with custom scopes."""
        with patch('app.routes.auth.authenticate_user', new_callable=AsyncMock) as mock_auth, \
             patch('app.routes.auth.create_access_token', new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            response = await client.post(
                "/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword",
                    "scope": "read write"
                }
            )
            
            assert response.status_code == 200
            
            # Verify token was created with custom scopes
            call_args = mock_token.call_args[1]
            assert call_args["data"]["scope"] == "read write"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials returns 401."""
        with patch('app.routes.auth.authenticate_user', new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = None  # Authentication failed
            
            response = await client.post(
                "/auth/login",
                data={
                    "username": "wronguser",
                    "password": "wrongpassword"
                }
            )
            
            assert response.status_code == 401
            data = response.json()
            assert "Incorrect username or password" in data["detail"]
            assert response.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_login_missing_username(self, client: AsyncClient):
        """Test login without username returns validation error."""
        response = await client.post(
            "/auth/login",
            data={
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """Test login without password returns validation error."""
        response = await client.post(
            "/auth/login",
            data={
                "username": "testuser"
            }
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login with empty credentials."""
        response = await client.post(
            "/auth/login",
            data={
                "username": "",
                "password": ""
            }
        )
        
        # Should still call authentication (which will fail)
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_login_token_includes_issuer(self, client: AsyncClient, mock_user: UserDetail):
        """Test that generated token includes issuer claim."""
        with patch('app.routes.auth.authenticate_user', new_callable=AsyncMock) as mock_auth, \
             patch('app.routes.auth.create_access_token', new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            response = await client.post(
                "/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword"
                }
            )
            
            assert response.status_code == 200
            
            # Verify issuer is included
            call_args = mock_token.call_args[1]
            assert "iss" in call_args["data"]
            assert "auth.baseklass.io" in call_args["data"]["iss"]

    @pytest.mark.asyncio
    async def test_login_returns_bearer_token_type(self, client: AsyncClient, mock_user: UserDetail):
        """Test that login always returns 'bearer' token type."""
        with patch('app.routes.auth.authenticate_user', new_callable=AsyncMock) as mock_auth, \
             patch('app.routes.auth.create_access_token', new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            response = await client.post(
                "/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["token_type"] == "bearer"

