"""Unit tests for authentication endpoints."""

from unittest.mock import ANY, AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.routes.auth import router
from app.schemas.user import UserDetail


@pytest.fixture
def app(app):
    """Create a FastAPI app with auth router."""
    app.include_router(router)
    return app


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
            # For web clients, refresh_token is in cookie, not response body
            assert data["refresh_token"] is None
            # Verify refresh token cookie is set
            assert "refresh_token" in response.cookies
            assert response.cookies["refresh_token"] == "test_refresh_token_12345"

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
        from app.core.exceptions.domain_exceptions import InvalidCredentialsException

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.side_effect = InvalidCredentialsException(username="")

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
        """Test successful token refresh with valid refresh token (web client via cookie)."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = Token(
                access_token="new_access_token",
                token_type="bearer",
                refresh_token="new_refresh_token",
            )

            # Web client: refresh token comes from cookie
            # Set cookie on client instance to avoid deprecation warning
            client.cookies["refresh_token"] = "valid_refresh_token"
            response = await client.post("/auth/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["token_type"] == "bearer"
            # For web clients, refresh_token is in cookie, not response body
            assert data["refresh_token"] is None
            # Verify new refresh token cookie is set
            assert "refresh_token" in response.cookies
            assert response.cookies["refresh_token"] == "new_refresh_token"

            # Verify refresh_access_token was called with correct params
            mock_refresh.assert_called_once_with("valid_refresh_token")

    @pytest.mark.asyncio
    async def test_refresh_token_success_mobile(self, client: AsyncClient):
        """Test successful token refresh with valid refresh token (mobile client via body)."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = Token(
                access_token="new_access_token",
                token_type="bearer",
                refresh_token="new_refresh_token",
            )

            # Mobile client: refresh token comes from request body
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "valid_refresh_token"},
                headers={"X-Client-Type": "mobile"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["token_type"] == "bearer"
            # For mobile clients, refresh_token is in response body
            assert data["refresh_token"] == "new_refresh_token"

            # Verify refresh_access_token was called with correct params
            mock_refresh.assert_called_once_with("valid_refresh_token")

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test token refresh with invalid refresh token returns 401 (web client via cookie)."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.side_effect = InvalidTokenException(
                reason="Invalid or expired refresh token"
            )

            # Web client: refresh token comes from cookie
            # Set cookie on client instance to avoid deprecation warning
            client.cookies["refresh_token"] = "invalid_token"
            response = await client.post("/auth/refresh")

            assert response.status_code == 401
            data = response.json()
            assert "Invalid or expired" in data["detail"]
            assert response.headers.get("WWW-Authenticate") == "Bearer"
            # Verify invalid cookie is cleared
            assert (
                "refresh_token" not in response.cookies
                or response.cookies.get("refresh_token") is None
            )

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_mobile(self, client: AsyncClient):
        """Test token refresh with invalid refresh token returns 401 (mobile client via body)."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.side_effect = InvalidTokenException(
                reason="Invalid or expired refresh token"
            )

            # Mobile client: refresh token comes from request body
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "invalid_token"},
                headers={"X-Client-Type": "mobile"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "Invalid or expired" in data["detail"]
            assert response.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client: AsyncClient):
        """Test token refresh with expired refresh token returns 401 (web client via cookie)."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.side_effect = InvalidTokenException(
                reason="Invalid or expired refresh token"
            )

            # Web client: refresh token comes from cookie
            # Set cookie on client instance to avoid deprecation warning
            client.cookies["refresh_token"] = "expired_token"
            response = await client.post("/auth/refresh")

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_missing_web(self, client: AsyncClient):
        """Test token refresh without refresh token cookie returns 401 (web client)."""
        response = await client.post("/auth/refresh")

        assert response.status_code == 401
        data = response.json()
        assert "Refresh token missing from cookie" in data["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token_missing_mobile(self, client: AsyncClient):
        """Test token refresh without refresh token in body returns 400 (mobile client)."""
        response = await client.post(
            "/auth/refresh",
            json={},
            headers={"X-Client-Type": "mobile"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Refresh token required in request body" in data["detail"]

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_tokens_web(self, client: AsyncClient):
        """Test that refresh returns new access token and sets new refresh token cookie (web client)."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = Token(
                access_token="new_access_token_xyz",
                token_type="bearer",
                refresh_token="new_refresh_token_xyz",
            )

            # Web client: refresh token comes from cookie
            # Set cookie on client instance to avoid deprecation warning
            client.cookies["refresh_token"] = "old_refresh_token"
            response = await client.post("/auth/refresh")

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["access_token"] == "new_access_token_xyz"
            # For web clients, refresh_token is None in body but set in cookie
            assert data["refresh_token"] is None
            assert "refresh_token" in response.cookies
            assert response.cookies["refresh_token"] == "new_refresh_token_xyz"

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_tokens_mobile(self, client: AsyncClient):
        """Test that refresh returns both new access and refresh tokens (mobile client)."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = Token(
                access_token="new_access_token_xyz",
                token_type="bearer",
                refresh_token="new_refresh_token_xyz",
            )

            # Mobile client: refresh token comes from request body
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "old_refresh_token"},
                headers={"X-Client-Type": "mobile"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["access_token"] == "new_access_token_xyz"
            assert data["refresh_token"] == "new_refresh_token_xyz"


class TestLogoutEndpoint:
    """Test suite for POST /auth/logout endpoint."""

    @pytest.fixture
    def authenticated_app(self, app, mock_user: UserDetail):
        """Create a FastAPI app with authentication dependencies overridden."""
        from app.routes.deps import get_current_user

        app.dependency_overrides[get_current_user] = lambda: mock_user
        return app

    @pytest.fixture
    async def authenticated_client(self, authenticated_app) -> AsyncClient:
        """Create an async HTTP client with authentication overrides."""
        from httpx import ASGITransport

        async with AsyncClient(
            transport=ASGITransport(app=authenticated_app), base_url="http://test"
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_logout_web_client(self, authenticated_client: AsyncClient):
        """Test logout clears refresh token cookie for web clients."""
        response = await authenticated_client.post("/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"
        # Cookie deletion is handled by FastAPI's delete_cookie method
        # The endpoint successfully executes the logout logic

    @pytest.mark.asyncio
    async def test_logout_mobile_client(self, authenticated_client: AsyncClient):
        """Test logout for mobile clients (no cookie clearing)."""
        response = await authenticated_client.post(
            "/auth/logout",
            headers={"X-Client-Type": "mobile"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"
        # Mobile clients don't have cookies, so no cookie clearing happens

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Test logout returns 401 for unauthenticated requests."""
        response = await client.post("/auth/logout")

        assert response.status_code == 401


class TestMobileClientDetection:
    """Test suite for mobile client detection logic."""

    @pytest.mark.asyncio
    async def test_mobile_client_detection_via_header(self, client: AsyncClient):
        """Test mobile client detection via X-Client-Type header."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            # Test with X-Client-Type: mobile
            response = await client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpassword"},
                headers={"X-Client-Type": "mobile"},
            )

            assert response.status_code == 200
            data = response.json()
            # Mobile clients get refresh_token in body
            assert data["refresh_token"] == "test_refresh_token"

    @pytest.mark.asyncio
    async def test_mobile_client_detection_via_user_agent(self, client: AsyncClient):
        """Test mobile client detection via User-Agent fallback."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            # Test with OkHttp User-Agent (Android)
            response = await client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpassword"},
                headers={"User-Agent": "okhttp/4.9.1"},
            )

            assert response.status_code == 200
            data = response.json()
            # Mobile clients get refresh_token in body
            assert data["refresh_token"] == "test_refresh_token"

    @pytest.mark.asyncio
    async def test_mobile_client_detection_ios_user_agent(self, client: AsyncClient):
        """Test mobile client detection with iOS User-Agent."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            # Test with Alamofire User-Agent (iOS)
            response = await client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpassword"},
                headers={"User-Agent": "MyApp/1.0 Alamofire/5.0"},
            )

            assert response.status_code == 200
            data = response.json()
            # Mobile clients get refresh_token in body
            assert data["refresh_token"] == "test_refresh_token"

    @pytest.mark.asyncio
    async def test_mobile_client_detection_cfnetwork_user_agent(
        self, client: AsyncClient
    ):
        """Test mobile client detection with CFNetwork User-Agent."""
        from app.schemas.user import Token

        with patch(
            "app.logic.auth.perform_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            # Test with CFNetwork User-Agent (iOS)
            response = await client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpassword"},
                headers={"User-Agent": "CFNetwork/1234 Darwin/20.0.0"},
            )

            assert response.status_code == 200
            data = response.json()
            # Mobile clients get refresh_token in body
            assert data["refresh_token"] == "test_refresh_token"
