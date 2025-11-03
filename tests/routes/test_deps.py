"""Unit tests for route dependencies."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import UnauthorizedException
from app.models import KPrincipal
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
        test_payload = {
            "sub": str(uuid4()),
            "scope": "test-scope",
            "iss": "test-issuer"
        }
        
        with patch('app.logic.deps.get_token_data', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = TokenData(**test_payload)
            
            result = await get_current_token("valid_token")
            
            assert isinstance(result, TokenData)
            assert result.sub == test_payload["sub"]
            assert result.scope == test_payload["scope"]
            assert result.iss == test_payload["iss"]
            mock_get_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_get_current_token_invalid_token(self):
        """Test that invalid token raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException
        
        with patch('app.logic.deps.get_token_data', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.side_effect = InvalidTokenException(reason="Token verification failed")
            
            with pytest.raises(UnauthorizedException):
                await get_current_token("invalid_token")

    @pytest.mark.asyncio
    async def test_get_current_token_missing_claims(self):
        """Test that token missing required claims raises error."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException
        
        with patch('app.logic.deps.get_token_data', new_callable=AsyncMock) as mock_get_token:
            # Logic layer would detect missing claims and raise exception
            mock_get_token.side_effect = InvalidTokenException(reason="Missing required claims")
            
            with pytest.raises(UnauthorizedException):
                await get_current_token("incomplete_token")


class TestGetCurrentUser:
    """Test suite for get_current_user dependency."""

    @pytest.fixture
    def mock_principal(self, creator_id):
        """Create a mock principal."""
        user_id = uuid4()
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
    async def test_get_current_user_success(self, async_session: AsyncSession, mock_principal: KPrincipal):
        """Test successful user retrieval from valid token."""
        async_session.add(mock_principal)
        await async_session.commit()
        await async_session.refresh(mock_principal)
        
        expected_user = UserDetail.model_validate(mock_principal)
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = expected_user
            
            result = await get_current_user("valid_token", async_session)
            
            assert isinstance(result, UserDetail)
            assert result.id == mock_principal.id
            assert result.username == "testuser"
            mock_get_user.assert_called_once_with("valid_token", async_session)
            assert result.primary_email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_session: AsyncSession):
        """Test that invalid token raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = InvalidTokenException(reason="Token verification failed")
            
            with pytest.raises(UnauthorizedException):
                await get_current_user("invalid_token", async_session)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_uuid(self, async_session: AsyncSession):
        """Test that invalid UUID in token raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidUserIdException
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = InvalidUserIdException(user_id_str="not-a-valid-uuid")
            
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user("token", async_session)
            
            assert "Invalid user ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, async_session: AsyncSession):
        """Test that non-existent user raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import UserNotFoundException
        
        non_existent_id = uuid4()
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = UserNotFoundException(user_id=non_existent_id)
            
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user("token", async_session)
            
            assert "User" in str(exc_info.value) and "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user_empty_sub(self, async_session: AsyncSession):
        """Test that empty sub claim raises UnauthorizedException."""
        from app.core.exceptions.domain_exceptions import InvalidUserIdException
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            # Empty string is invalid UUID
            mock_get_user.side_effect = InvalidUserIdException(user_id_str="")
            
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user("token", async_session)
            
            # Empty string is invalid UUID, so we get "Invalid user ID" error
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
    async def test_get_optional_user_no_auth_header(self, mock_request, async_session: AsyncSession):
        """Test that missing auth header returns None."""
        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_format(self, mock_request, async_session: AsyncSession):
        """Test that invalid auth header format returns None."""
        mock_request.headers = {"Authorization": "InvalidFormat"}
        
        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_not_bearer(self, mock_request, async_session: AsyncSession):
        """Test that non-Bearer token type returns None."""
        mock_request.headers = {"Authorization": "Basic sometoken"}
        
        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_empty_token(self, mock_request, async_session: AsyncSession):
        """Test that empty token returns None."""
        mock_request.headers = {"Authorization": "Bearer "}
        
        result = await get_optional_user(mock_request, async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_token_returns_none(self, mock_request, async_session: AsyncSession):
        """Test that invalid token returns None (doesn't raise)."""
        from app.core.exceptions.domain_exceptions import InvalidTokenException
        
        mock_request.headers = {"Authorization": "Bearer invalid_token"}
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = InvalidTokenException(reason="Token verification failed")
            
            result = await get_optional_user(mock_request, async_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_handles_401_exception(self, mock_request, async_session: AsyncSession):
        """Test that 401 exceptions are caught and return None."""
        mock_request.headers = {"Authorization": "Bearer some_token"}
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Unauthorized")
            
            result = await get_optional_user(mock_request, async_session)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_handles_generic_exception(self, mock_request, async_session: AsyncSession):
        """Test that generic exceptions are caught and return None."""
        mock_request.headers = {"Authorization": "Bearer some_token"}
        
        with patch('app.logic.deps.get_user_from_token', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = Exception("Some error")
            
            result = await get_optional_user(mock_request, async_session)
            assert result is None


class TestGetCurrentSuperuser:
    """Test suite for get_current_superuser dependency."""

    @pytest.fixture
    def regular_user(self, creator_id):
        """Create a regular user without superuser privileges."""
        user_id = uuid4()
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
            system_role="system_user",
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

    @pytest.fixture
    def superuser(self, creator_id):
        """Create a superuser with elevated privileges."""
        user_id = uuid4()
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
            system_role="admin",
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
    async def test_get_current_superuser_regular_user_denied(self, regular_user: UserDetail):
        """Test that regular user is denied superuser access."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(regular_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient privileges" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_superuser_missing_flag(self, creator_id):
        """Test that user without superuser flag in meta is denied."""
        user_id = uuid4()
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
            system_role="system_user",
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
        user_id = uuid4()
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
            system_role="system_user",
            meta={"is_superuser": False},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(user)
        
        assert exc_info.value.status_code == 403

