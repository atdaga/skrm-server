"""Unit tests for route dependencies."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import UnauthorizedException
from app.models import KPrincipal
from app.models.k_principal import SystemRole
from app.routes.deps import (
    get_current_superuser,
    get_current_token,
    get_current_user,
    get_optional_user,
)
from app.schemas.user import TokenData, UserDetail


class TestGetCurrentToken:
    """Test suite for get_current_token dependency."""

    @pytest.mark.asyncio
    async def test_get_current_token_success(self):
        """Test successful token extraction and validation."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        # No cache in request.state

        now = datetime.now(UTC).replace(tzinfo=None)
        test_payload = {
            "sub": str(uuid7()),
            "scope": "test-scope",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
            "iat": now,
            "exp": now,
            "ss": now,
        }

        with patch(
            "app.logic.deps.get_token_data", new_callable=AsyncMock
        ) as mock_get_token:
            mock_get_token.return_value = TokenData(**test_payload)

            result = await get_current_token(mock_request, "valid_token")

            assert isinstance(result, TokenData)
            assert result.sub == test_payload["sub"]
            assert result.scope == test_payload["scope"]
            assert result.iss == test_payload["iss"]
            assert result.aud == test_payload["aud"]
            assert result.jti == test_payload["jti"]
            mock_get_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_get_current_token_invalid_token(self):
        """Test that invalid token raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with patch(
            "app.logic.deps.get_token_data", new_callable=AsyncMock
        ) as mock_get_token:
            mock_get_token.side_effect = InvalidTokenException(
                reason="Token verification failed"
            )

            with pytest.raises(UnauthorizedException):
                await get_current_token(mock_request, "invalid_token")

    @pytest.mark.asyncio
    async def test_get_current_token_missing_claims(self):
        """Test that token missing required claims raises error."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with patch(
            "app.logic.deps.get_token_data", new_callable=AsyncMock
        ) as mock_get_token:
            # Logic layer would detect missing claims and raise exception
            mock_get_token.side_effect = InvalidTokenException(
                reason="Missing required claims"
            )

            with pytest.raises(UnauthorizedException):
                await get_current_token(mock_request, "incomplete_token")

    @pytest.mark.asyncio
    async def test_get_current_token_uses_cache_when_available(self):
        """Test that get_current_token uses cached payload from middleware."""
        mock_request = MagicMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        # Set up cached payload in request.state
        cached_payload = {
            "sub": str(uuid7()),
            "scope": "test-scope",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
        }
        mock_request.state.jwt_token = "valid_token"
        mock_request.state.jwt_payload = cached_payload

        with patch(
            "app.logic.deps.get_token_data", new_callable=AsyncMock
        ) as mock_get_token:
            # Should NOT be called when cache is available
            result = await get_current_token(mock_request, "valid_token")

            # Verify the result is correct
            assert isinstance(result, TokenData)
            assert result.sub == cached_payload["sub"]
            assert result.scope == cached_payload["scope"]
            assert result.iss == cached_payload["iss"]
            assert result.aud == cached_payload["aud"]
            assert result.jti == cached_payload["jti"]

            # Verify get_token_data was NOT called (cache hit)
            mock_get_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_token_skips_cache_on_token_mismatch(self):
        """Test that get_current_token validates when cached token doesn't match."""
        mock_request = MagicMock()
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        # Set up cached payload for different token
        cached_payload = {
            "sub": str(uuid7()),
            "scope": "test-scope",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,
            "ss": now_ts,
        }
        mock_request.state.jwt_token = "different_token"  # Mismatch
        mock_request.state.jwt_payload = cached_payload

        with patch(
            "app.logic.deps.get_token_data", new_callable=AsyncMock
        ) as mock_get_token:
            mock_get_token.return_value = TokenData(
                sub=str(uuid7()),
                scope="new-scope",
                iss="new-issuer",
                aud="new-audience",
                jti=str(uuid7()),
                iat=now,
                exp=now,
                ss=now,
            )

            result = await get_current_token(mock_request, "valid_token")

            # Verify get_token_data WAS called (cache miss due to token mismatch)
            mock_get_token.assert_called_once_with("valid_token")
            assert result.scope == "new-scope"


class TestGetCurrentUser:
    """Test suite for get_current_user dependency."""

    @pytest.fixture
    def mock_principal(self, creator_id):
        """Create a mock principal."""
        user_id = uuid7()
        return KPrincipal(
            id=user_id,
            scope="global",
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self, async_session: AsyncSession, mock_principal: KPrincipal
    ):
        """Test successful user retrieval from valid token."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()

        async_session.add(mock_principal)
        await async_session.commit()
        await async_session.refresh(mock_principal)

        expected_user = UserDetail.model_validate(mock_principal)

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = expected_user

            result = await get_current_user(mock_request, "valid_token", async_session)

            assert isinstance(result, UserDetail)
            assert result.id == mock_principal.id
            assert result.username == "testuser"
            mock_get_user.assert_called_once_with("valid_token", async_session)
            assert result.primary_email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_session: AsyncSession):
        """Test that invalid token raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.side_effect = InvalidTokenException(
                reason="Token verification failed"
            )

            with pytest.raises(UnauthorizedException):
                await get_current_user(mock_request, "invalid_token", async_session)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_uuid(self, async_session: AsyncSession):
        """Test that invalid UUID in token raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidUserIdException

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.side_effect = InvalidUserIdException(
                user_id_str="not-a-valid-uuid"
            )

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(mock_request, "token", async_session)

            assert "Invalid user ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, async_session: AsyncSession):
        """Test that non-existent user raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import UserNotFoundException

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        non_existent_id = uuid7()

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.side_effect = UserNotFoundException(user_id=non_existent_id)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(mock_request, "token", async_session)

            assert "User" in str(exc_info.value) and "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_empty_sub(self, async_session: AsyncSession):
        """Test that empty sub claim raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidUserIdException

        mock_request = MagicMock()
        mock_request.state = MagicMock()

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            # Empty string is invalid UUID
            mock_get_user.side_effect = InvalidUserIdException(user_id_str="")

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(mock_request, "token", async_session)

            # Empty string is invalid UUID, so we get "Invalid user ID" error
            assert "Invalid user ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_uses_cache_when_available(
        self, async_session: AsyncSession, mock_principal: KPrincipal
    ):
        """Test that get_current_user uses cached payload from middleware."""
        mock_request = MagicMock()

        # Add principal to database
        async_session.add(mock_principal)
        await async_session.commit()
        await async_session.refresh(mock_principal)

        # Set up cached payload in request.state
        cached_payload = {
            "sub": str(mock_principal.id),
            "scope": "global",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
        }
        mock_request.state.jwt_token = "valid_token"
        mock_request.state.jwt_payload = cached_payload

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user_from_token:
            # Should NOT be called when cache is available
            result = await get_current_user(mock_request, "valid_token", async_session)

            # Verify the result is correct
            assert isinstance(result, UserDetail)
            assert result.id == mock_principal.id
            assert result.username == mock_principal.username

            # Verify get_user_from_token was NOT called (cache hit)
            mock_get_user_from_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_uuid_in_cache(
        self, async_session: AsyncSession
    ):
        """Test that invalid UUID in cached payload raises UnauthorizedException."""

        mock_request = MagicMock()

        # Set up cached payload with invalid UUID
        cached_payload = {
            "sub": "not-a-valid-uuid",
            "scope": "global",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
        }
        mock_request.state.jwt_token = "valid_token"
        mock_request.state.jwt_payload = cached_payload

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(mock_request, "valid_token", async_session)

        assert "Invalid user ID" in str(exc_info.value)


class TestGetOptionalUser:
    """Test suite for get_optional_user dependency."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock()
        request.headers = {}
        return request

    @pytest.mark.asyncio
    async def test_get_optional_user_no_auth_header(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that missing auth header returns None."""
        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_format(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that invalid auth header format returns None."""
        mock_request.headers = {"Authorization": "InvalidFormat"}

        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_not_bearer(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that non-Bearer token type returns None."""
        mock_request.headers = {"Authorization": "Basic sometoken"}

        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_empty_token(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that empty token returns None."""
        mock_request.headers = {"Authorization": "Bearer "}

        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_token_returns_none(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that invalid token returns None (doesn't raise)."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException

        mock_request.headers = {"Authorization": "Bearer invalid_token"}

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.side_effect = InvalidTokenException(
                reason="Token verification failed"
            )

            result = await get_optional_user(mock_request, async_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_handles_401_exception(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that 401 exceptions are caught and return None."""
        mock_request.headers = {"Authorization": "Bearer some_token"}

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.side_effect = HTTPException(
                status_code=401, detail="Unauthorized"
            )

            result = await get_optional_user(mock_request, async_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_handles_generic_exception(
        self, mock_request, async_session: AsyncSession
    ):
        """Test that generic exceptions are caught and return None."""
        mock_request.headers = {"Authorization": "Bearer some_token"}

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.side_effect = Exception("Some error")

            result = await get_optional_user(mock_request, async_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_uses_cache_when_available(
        self, async_session: AsyncSession, creator_id
    ):
        """Test that get_optional_user uses cached payload from middleware."""
        from app.models import KPrincipal

        # Create and save a principal
        user_id = uuid7()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        await async_session.refresh(principal)

        # Set up mock request with cached payload
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        cached_payload = {
            "sub": str(user_id),
            "scope": "global",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
        }
        mock_request.state.jwt_token = "valid_token"
        mock_request.state.jwt_payload = cached_payload

        with patch(
            "app.logic.deps.get_user_from_token", new_callable=AsyncMock
        ) as mock_get_user_from_token:
            # Should NOT be called when cache is available
            result = await get_optional_user(mock_request, async_session)

            # Verify the result is correct
            assert result is not None
            assert isinstance(result, UserDetail)
            assert result.id == user_id
            assert result.username == "testuser"

            # Verify get_user_from_token was NOT called (cache hit)
            mock_get_user_from_token.assert_not_called()


class TestGetCurrentSuperuser:
    """Test suite for get_current_superuser dependency."""

    @pytest.fixture
    def regular_user(self, creator_id):
        """Create a regular user without superuser privileges."""
        user_id = uuid7()
        now = datetime.now()
        return UserDetail(
            id=user_id,
            scope="global",
            username="regularuser",
            primary_email="regular@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="Regular",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="Regular User",
            default_locale="en",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

    @pytest.fixture
    def superuser(self, creator_id):
        """Create a superuser with elevated privileges."""
        user_id = uuid7()
        now = datetime.now()
        return UserDetail(
            id=user_id,
            scope="global",
            username="superuser",
            primary_email="super@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="Super",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="Super User",
            default_locale="en",
            system_role=SystemRole.SYSTEM_ADMIN,
            meta={"is_superuser": True},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

    @pytest.mark.asyncio
    async def test_get_current_superuser_success(self, superuser: UserDetail):
        """Test that superuser is returned for user with superuser flag."""
        result = await get_current_superuser(superuser)

        assert result == superuser
        assert result.meta.get("is_superuser") is True

    @pytest.mark.asyncio
    async def test_get_current_superuser_regular_user_denied(
        self, regular_user: UserDetail
    ):
        """Test that regular user is denied superuser access."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(regular_user)

        assert exc_info.value.status_code == 403
        assert "Insufficient privileges" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_superuser_missing_flag(self, creator_id):
        """Test that user without superuser flag in meta is denied."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="user",
            primary_email="user@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="User",
            middle_name=None,
            last_name="Name",
            name_suffix=None,
            display_name="User Name",
            default_locale="en",
            system_role=SystemRole.SYSTEM_USER,
            meta={"other_field": "value"},  # No is_superuser field
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_current_superuser_false_flag(self, creator_id):
        """Test that user with is_superuser=False is denied."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="user",
            primary_email="user@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="User",
            middle_name=None,
            last_name="Name",
            name_suffix=None,
            display_name="User Name",
            default_locale="en",
            system_role=SystemRole.SYSTEM_USER,
            meta={"is_superuser": False},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(user)

        assert exc_info.value.status_code == 403
