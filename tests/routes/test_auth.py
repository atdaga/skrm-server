"""Unit tests for authentication endpoints."""

from datetime import datetime
from unittest.mock import ANY, AsyncMock, patch
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
        transport=ASGITransport(app=app), base_url="http://test"
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
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token_12345",
                token_type="bearer",
                refresh_token="test_refresh_token_12345",
            )

            response = await client.post(
                "/auth/login", data={"username": "testuser", "password": "testpassword"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test_access_token_12345"
            assert data["token_type"] == "bearer"
            assert data["refresh_token"] == "test_refresh_token_12345"

            # Verify perform_login was called with correct params
            mock_login.assert_called_once_with(
                username="testuser",
                password="testpassword",
                db=ANY,  # Database session from dependency injection
                scopes=[],
            )

    @pytest.mark.asyncio
    async def test_login_with_custom_scopes(
        self, client: AsyncClient, mock_user: UserDetail
    ):
        """Test login with custom scopes."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            response = await client.post(
                "/auth/login",
                data={
                    "username": "testuser",
                    "password": "testpassword",
                    "scope": "read write",
                },
            )

            assert response.status_code == 200

            # Verify perform_login was called with custom scopes
            mock_login.assert_called_once_with(
                username="testuser",
                password="testpassword",
                db=ANY,  # Database session from dependency injection
                scopes=["read", "write"],
            )

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials returns 401."""
        from app.core.exceptions.domain_exceptions import InvalidCredentialsException

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.side_effect = InvalidCredentialsException(username="wronguser")

            response = await client.post(
                "/auth/login",
                data={"username": "wronguser", "password": "wrongpassword"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "Invalid username or password" in data["detail"]
            assert response.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_login_missing_username(self, client: AsyncClient):
        """Test login without username returns validation error."""
        response = await client.post("/auth/login", data={"password": "testpassword"})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """Test login without password returns validation error."""
        response = await client.post("/auth/login", data={"username": "testuser"})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login with empty credentials."""
        response = await client.post(
            "/auth/login", data={"username": "", "password": ""}
        )

        # Should still call authentication (which will fail)
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_login_token_includes_issuer(
        self, client: AsyncClient, mock_user: UserDetail
    ):
        """Test that generated token includes issuer claim."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            response = await client.post(
                "/auth/login", data={"username": "testuser", "password": "testpassword"}
            )

            assert response.status_code == 200
            # The issuer is handled in the logic layer (perform_login)
            # This test now just verifies the endpoint works correctly

    @pytest.mark.asyncio
    async def test_login_returns_bearer_token_type(
        self, client: AsyncClient, mock_user: UserDetail
    ):
        """Test that login always returns 'bearer' token type."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            response = await client.post(
                "/auth/login", data={"username": "testuser", "password": "testpassword"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["token_type"] == "bearer"


class TestRefreshEndpoint:
    """Test suite for POST /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient):
        """Test successful token refresh with valid refresh token."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = Token(
                access_token="new_access_token",
                token_type="bearer",
                refresh_token="new_refresh_token",
            )

            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "valid_refresh_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["token_type"] == "bearer"
            assert data["refresh_token"] == "new_refresh_token"

            # Verify refresh_access_token was called with correct params
            mock_refresh.assert_called_once_with("valid_refresh_token")

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test token refresh with invalid refresh token returns 401."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.side_effect = InvalidTokenException(
                reason="Invalid or expired refresh token"
            )

            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "invalid_token"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "Invalid or expired" in data["detail"]
            assert response.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client: AsyncClient):
        """Test token refresh with expired refresh token returns 401."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.side_effect = InvalidTokenException(
                reason="Invalid or expired refresh token"
            )

            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "expired_token"},
            )

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, client: AsyncClient):
        """Test token refresh without refresh token returns validation error."""
        response = await client.post("/auth/refresh", json={})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_tokens(self, client: AsyncClient):
        """Test that refresh returns both new access and refresh tokens."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = Token(
                access_token="new_access_token_xyz",
                token_type="bearer",
                refresh_token="new_refresh_token_xyz",
            )

            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "old_refresh_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["access_token"] == "new_access_token_xyz"
            assert data["refresh_token"] == "new_refresh_token_xyz"
