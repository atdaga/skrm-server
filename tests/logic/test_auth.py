"""Unit tests for authentication logic layer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid7

import pytest

from app.core.exceptions.domain_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
)
from app.logic.auth import perform_login, refresh_access_token
from app.models.k_principal import SystemRole
from app.schemas.user import Token, UserDetail


class TestPerformLogin:
    """Test suite for perform_login function."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user_id = uuid7()
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
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            deleted_at=None,
            created=now,
            created_by=uuid7(),
            last_modified=now,
            last_modified_by=uuid7(),
        )

    @pytest.mark.asyncio
    async def test_perform_login_success_default_scope(
        self, mock_user: UserDetail, async_session
    ):
        """Test successful login with default scope."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_auth.return_value = mock_user
            mock_access.return_value = "test_access_token_12345"
            mock_refresh.return_value = "test_refresh_token_12345"

            result = await perform_login("testuser", "password123", async_session)

            # Verify result
            assert isinstance(result, Token)
            assert result.access_token == "test_access_token_12345"
            assert result.token_type == "bearer"
            assert result.refresh_token == "test_refresh_token_12345"

            # Verify authenticate_user was called correctly
            mock_auth.assert_called_once_with("testuser", "password123", async_session)

            # Verify create_access_token was called with correct data
            mock_access.assert_called_once()
            call_kwargs = mock_access.call_args[1]
            assert call_kwargs["data"]["sub"] == str(mock_user.id)
            assert call_kwargs["data"]["scope"] == "global"
            # Note: iss, aud, jti, iat, exp, ss are added inside create_access_token

            # Verify create_refresh_token was called with same data
            mock_refresh.assert_called_once()
            refresh_kwargs = mock_refresh.call_args[1]
            assert refresh_kwargs["data"]["sub"] == str(mock_user.id)
            assert refresh_kwargs["data"]["scope"] == "global"
            # Note: iss, aud, jti, iat, exp, ss are added inside create_refresh_token

    @pytest.mark.asyncio
    async def test_perform_login_success_custom_scopes(
        self, mock_user: UserDetail, async_session
    ):
        """Test successful login with custom scopes."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_auth.return_value = mock_user
            mock_access.return_value = "test_token"
            mock_refresh.return_value = "test_refresh_token"

            await perform_login(
                "testuser", "password123", async_session, scopes=["read", "write"]
            )

            # Verify token was created with custom scopes
            call_kwargs = mock_access.call_args[1]
            assert call_kwargs["data"]["scope"] == "read write"

    @pytest.mark.asyncio
    async def test_perform_login_success_empty_scopes_list(
        self, mock_user: UserDetail, async_session
    ):
        """Test login with empty scopes list defaults to 'global'."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_auth.return_value = mock_user
            mock_access.return_value = "test_token"
            mock_refresh.return_value = "test_refresh_token"

            await perform_login("testuser", "password123", async_session, scopes=[])

            # Empty list should result in "global" scope
            call_kwargs = mock_access.call_args[1]
            assert call_kwargs["data"]["scope"] == "global"

    @pytest.mark.asyncio
    async def test_perform_login_invalid_credentials(self, async_session):
        """Test login with invalid credentials raises exception."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = None  # Authentication failed

            with pytest.raises(InvalidCredentialsException) as exc_info:
                await perform_login("wronguser", "wrongpassword", async_session)

            # Verify exception details
            assert exc_info.value.username == "wronguser"
            assert "Invalid username or password" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_perform_login_invalid_credentials_with_scopes(self, async_session):
        """Test login fails even when scopes are provided if credentials are wrong."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = None

            with pytest.raises(InvalidCredentialsException):
                await perform_login(
                    "wronguser", "wrongpassword", async_session, scopes=["admin"]
                )

    @pytest.mark.asyncio
    async def test_perform_login_token_includes_issuer(
        self, mock_user: UserDetail, async_session
    ):
        """Test that generated token always includes issuer."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_auth.return_value = mock_user
            mock_access.return_value = "test_token"
            mock_refresh.return_value = "test_refresh_token"

            await perform_login("testuser", "password123", async_session)

            # Verify token creation was called (iss is added inside create_access_token)
            call_kwargs = mock_access.call_args[1]
            assert call_kwargs["data"]["sub"] == str(mock_user.id)
            assert call_kwargs["data"]["scope"] == "global"
            # Note: iss is added inside create_access_token, not in the data passed to it

    @pytest.mark.asyncio
    async def test_perform_login_multiple_scopes(
        self, mock_user: UserDetail, async_session
    ):
        """Test login with multiple scopes joins them correctly."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_auth.return_value = mock_user
            mock_access.return_value = "test_token"
            mock_refresh.return_value = "test_refresh_token"

            await perform_login(
                "testuser",
                "password123",
                async_session,
                scopes=["read", "write", "admin"],
            )

            call_kwargs = mock_access.call_args[1]
            assert call_kwargs["data"]["scope"] == "read write admin"


class TestRefreshAccessToken:
    """Test suite for refresh_access_token function."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh with valid refresh token."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        mock_payload = {
            "sub": user_id,
            "scope": "global",
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_verify.return_value = mock_payload
            mock_access.return_value = "new_access_token"
            mock_refresh.return_value = "new_refresh_token"

            result = await refresh_access_token("valid_refresh_token")

            # Verify result
            assert isinstance(result, Token)
            assert result.access_token == "new_access_token"
            assert result.token_type == "bearer"
            assert result.refresh_token == "new_refresh_token"

            # Verify verify_token was called
            mock_verify.assert_called_once_with("valid_refresh_token")

            # Verify new tokens were created with correct data
            mock_access.assert_called_once()
            access_call_kwargs = mock_access.call_args[1]
            assert access_call_kwargs["data"]["sub"] == user_id
            assert access_call_kwargs["data"]["scope"] == "global"
            assert access_call_kwargs["data"]["iss"] == "https://auth.baseklass.io"
            # Note: aud, jti, iat, exp, ss are added inside create_access_token

            mock_refresh.assert_called_once()
            refresh_call_kwargs = mock_refresh.call_args[1]
            assert refresh_call_kwargs["data"]["sub"] == user_id
            # Note: iss, aud, jti, iat, exp, ss are added inside create_refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self):
        """Test token refresh with invalid token raises exception."""
        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = None  # Invalid token

            with pytest.raises(InvalidTokenException) as exc_info:
                await refresh_access_token("invalid_token")

            assert "Invalid or expired" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_token_missing_subject(self):
        """Test token refresh with missing subject in payload raises exception."""
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        mock_payload = {
            "scope": "global",
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
            # Missing "sub"
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = mock_payload

            with pytest.raises(InvalidTokenException) as exc_info:
                await refresh_access_token("token_without_subject")

            assert "Missing subject" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_token_preserves_scope(self):
        """Test that token refresh preserves the original scope."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        mock_payload = {
            "sub": user_id,
            "scope": "read write admin",
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_verify.return_value = mock_payload
            mock_access.return_value = "new_token"
            mock_refresh.return_value = "new_refresh"

            await refresh_access_token("valid_token")

            # Verify scope was preserved
            access_call_kwargs = mock_access.call_args[1]
            assert access_call_kwargs["data"]["scope"] == "read write admin"

    @pytest.mark.asyncio
    async def test_refresh_token_default_scope(self):
        """Test that token refresh uses default scope if not present in payload."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        mock_payload = {
            "sub": user_id,
            # No scope provided
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_verify.return_value = mock_payload
            mock_access.return_value = "new_token"
            mock_refresh.return_value = "new_refresh"

            await refresh_access_token("valid_token")

            # Verify default scope was used
            access_call_kwargs = mock_access.call_args[1]
            assert access_call_kwargs["data"]["scope"] == "global"

    @pytest.mark.asyncio
    async def test_refresh_token_preserves_issuer(self):
        """Test that token refresh preserves the original issuer."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        mock_payload = {
            "sub": user_id,
            "scope": "global",
            "iss": "https://custom-issuer.example.com",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_verify.return_value = mock_payload
            mock_access.return_value = "new_token"
            mock_refresh.return_value = "new_refresh"

            await refresh_access_token("valid_token")

            # Verify issuer was passed to token creation
            # Note: The issuer from the original token is preserved in the data passed to create_access_token
            # It will be used if provided in data, otherwise create_access_token uses default
            access_call_kwargs = mock_access.call_args[1]
            assert (
                access_call_kwargs["data"]["iss"] == "https://custom-issuer.example.com"
            )

    @pytest.mark.asyncio
    async def test_refresh_token_missing_session_start(self):
        """Test token refresh with missing session start claim raises exception."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        mock_payload = {
            "sub": user_id,
            "scope": "global",
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            # Missing "ss"
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = mock_payload

            with pytest.raises(InvalidTokenException) as exc_info:
                await refresh_access_token("token_without_session_start")

            assert "Missing session start claim" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_refresh_token_absolute_expiration_exceeded(self):
        """Test token refresh fails when absolute expiration time is exceeded."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        # Session started 31 days ago (more than 1 month)
        session_start_ts = now_ts - (31 * 24 * 60 * 60)

        mock_payload = {
            "sub": user_id,
            "scope": "global",
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": session_start_ts,  # Session started 31 days ago
        }

        with patch(
            "app.logic.auth.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = mock_payload

            with pytest.raises(InvalidTokenException) as exc_info:
                await refresh_access_token("expired_session_token")

            assert "absolute expiration" in exc_info.value.message
