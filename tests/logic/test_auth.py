"""Unit tests for authentication logic layer."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions.domain_exceptions import InvalidCredentialsException
from app.logic.auth import perform_login
from app.schemas.user import Token, UserDetail


class TestPerformLogin:
    """Test suite for perform_login function."""

    @pytest.fixture
    def mock_user(self):
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
            created_by=uuid4(),
            last_modified=now,
            last_modified_by=uuid4(),
        )

    @pytest.mark.asyncio
    async def test_perform_login_success_default_scope(self, mock_user: UserDetail, async_session):
        """Test successful login with default scope."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth, \
             patch("app.logic.auth.create_access_token", new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_access_token_12345"
            
            result = await perform_login("testuser", "password123", async_session)
            
            # Verify result
            assert isinstance(result, Token)
            assert result.access_token == "test_access_token_12345"
            assert result.token_type == "bearer"
            
            # Verify authenticate_user was called correctly
            mock_auth.assert_called_once_with("testuser", "password123", async_session)
            
            # Verify create_access_token was called with correct data
            mock_token.assert_called_once()
            call_kwargs = mock_token.call_args[1]
            assert call_kwargs["data"]["sub"] == str(mock_user.id)
            assert call_kwargs["data"]["scope"] == "global"
            assert call_kwargs["data"]["iss"] == "https://auth.baseklass.io"

    @pytest.mark.asyncio
    async def test_perform_login_success_custom_scopes(self, mock_user: UserDetail, async_session):
        """Test successful login with custom scopes."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth, \
             patch("app.logic.auth.create_access_token", new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            result = await perform_login("testuser", "password123", async_session, scopes=["read", "write"])
            
            # Verify token was created with custom scopes
            call_kwargs = mock_token.call_args[1]
            assert call_kwargs["data"]["scope"] == "read write"

    @pytest.mark.asyncio
    async def test_perform_login_success_empty_scopes_list(self, mock_user: UserDetail, async_session):
        """Test login with empty scopes list defaults to 'global'."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth, \
             patch("app.logic.auth.create_access_token", new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            result = await perform_login("testuser", "password123", async_session, scopes=[])
            
            # Empty list should result in "global" scope
            call_kwargs = mock_token.call_args[1]
            assert call_kwargs["data"]["scope"] == "global"

    @pytest.mark.asyncio
    async def test_perform_login_invalid_credentials(self, async_session):
        """Test login with invalid credentials raises exception."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = None  # Authentication failed
            
            with pytest.raises(InvalidCredentialsException) as exc_info:
                await perform_login("wronguser", "wrongpassword", async_session)
            
            # Verify exception details
            assert exc_info.value.username == "wronguser"
            assert "Invalid username or password" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_perform_login_invalid_credentials_with_scopes(self, async_session):
        """Test login fails even when scopes are provided if credentials are wrong."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = None
            
            with pytest.raises(InvalidCredentialsException):
                await perform_login("wronguser", "wrongpassword", async_session, scopes=["admin"])

    @pytest.mark.asyncio
    async def test_perform_login_token_includes_issuer(self, mock_user: UserDetail, async_session):
        """Test that generated token always includes issuer."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth, \
             patch("app.logic.auth.create_access_token", new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            await perform_login("testuser", "password123", async_session)
            
            # Verify issuer is included
            call_kwargs = mock_token.call_args[1]
            assert "iss" in call_kwargs["data"]
            assert call_kwargs["data"]["iss"] == "https://auth.baseklass.io"

    @pytest.mark.asyncio
    async def test_perform_login_multiple_scopes(self, mock_user: UserDetail, async_session):
        """Test login with multiple scopes joins them correctly."""
        with patch("app.logic.auth.authenticate_user", new_callable=AsyncMock) as mock_auth, \
             patch("app.logic.auth.create_access_token", new_callable=AsyncMock) as mock_token:
            
            mock_auth.return_value = mock_user
            mock_token.return_value = "test_token"
            
            await perform_login("testuser", "password123", async_session, scopes=["read", "write", "admin"])
            
            call_kwargs = mock_token.call_args[1]
            assert call_kwargs["data"]["scope"] == "read write admin"

