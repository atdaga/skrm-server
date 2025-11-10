"""Unit tests for dependency logic layer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid7

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    InvalidTokenException,
    InvalidUserIdException,
    UserNotFoundException,
)
from app.logic.deps import (
    check_superuser_privileges,
    check_system_user_role,
    get_token_data,
    get_user_by_id,
    get_user_from_token,
)
from app.models import KPrincipal
from app.models.k_principal import SystemRole
from app.schemas.user import TokenData, UserDetail


class TestGetTokenData:
    """Test suite for get_token_data function."""

    @pytest.mark.asyncio
    async def test_get_token_data_success(self):
        """Test successful token data extraction."""
        now = datetime.now(UTC).replace(tzinfo=None)
        now_ts = int(now.replace(tzinfo=UTC).timestamp())

        test_payload = {
            "sub": str(uuid7()),
            "scope": "test-scope",
            "iss": "test-issuer",
            "aud": "test-audience",
            "jti": str(uuid7()),
            "iat": now_ts,
            "exp": now_ts + 1800,  # 30 minutes later
            "ss": now_ts,  # session start
        }

        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = test_payload

            result = await get_token_data("valid_token")

            assert isinstance(result, TokenData)
            assert result.sub == test_payload["sub"]
            assert result.scope == test_payload["scope"]
            assert result.iss == test_payload["iss"]
            assert result.aud == test_payload["aud"]
            assert result.jti == test_payload["jti"]
            assert isinstance(result.iat, datetime)
            assert isinstance(result.exp, datetime)
            assert isinstance(result.ss, datetime)
            mock_verify.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_get_token_data_invalid_token(self):
        """Test that invalid token raises InvalidTokenException."""
        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = None

            with pytest.raises(InvalidTokenException) as exc_info:
                await get_token_data("invalid_token")

            assert "Token verification failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_token_data_expired_token(self):
        """Test that expired token raises InvalidTokenException."""
        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = (
                None  # verify_token returns None for expired tokens
            )

            with pytest.raises(InvalidTokenException):
                await get_token_data("expired_token")


class TestGetUserById:
    """Test suite for get_user_by_id function."""

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
    async def test_get_user_by_id_success(
        self, async_session: AsyncSession, mock_principal: KPrincipal
    ):
        """Test successful user retrieval by ID."""
        async_session.add(mock_principal)
        await async_session.commit()
        await async_session.refresh(mock_principal)

        result = await get_user_by_id(mock_principal.id, async_session)

        assert isinstance(result, UserDetail)
        assert result.id == mock_principal.id
        assert result.username == mock_principal.username
        assert result.primary_email == mock_principal.primary_email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, async_session: AsyncSession):
        """Test that non-existent user raises UserNotFoundException."""
        non_existent_id = uuid7()

        with pytest.raises(UserNotFoundException) as exc_info:
            await get_user_by_id(non_existent_id, async_session)

        assert exc_info.value.user_id == non_existent_id
        assert str(non_existent_id) in exc_info.value.message


class TestGetUserFromToken:
    """Test suite for get_user_from_token function."""

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
    async def test_get_user_from_token_success(
        self, async_session: AsyncSession, mock_principal: KPrincipal
    ):
        """Test successful user retrieval from valid token."""
        async_session.add(mock_principal)
        await async_session.commit()
        await async_session.refresh(mock_principal)

        test_payload = {"sub": str(mock_principal.id), "scope": "global", "iss": "test"}

        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = test_payload

            result = await get_user_from_token("valid_token", async_session)

            assert isinstance(result, UserDetail)
            assert result.id == mock_principal.id
            assert result.username == mock_principal.username

    @pytest.mark.asyncio
    async def test_get_user_from_token_invalid_token(self, async_session: AsyncSession):
        """Test that invalid token raises InvalidTokenException."""
        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = None

            with pytest.raises(InvalidTokenException):
                await get_user_from_token("invalid_token", async_session)

    @pytest.mark.asyncio
    async def test_get_user_from_token_invalid_uuid(self, async_session: AsyncSession):
        """Test that invalid UUID raises InvalidUserIdException."""
        test_payload = {"sub": "not-a-valid-uuid", "scope": "global", "iss": "test"}

        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = test_payload

            with pytest.raises(InvalidUserIdException) as exc_info:
                await get_user_from_token("token", async_session)

            assert exc_info.value.user_id_str == "not-a-valid-uuid"

    @pytest.mark.asyncio
    async def test_get_user_from_token_empty_sub(self, async_session: AsyncSession):
        """Test that empty sub claim raises InvalidUserIdException."""
        test_payload = {"sub": "", "scope": "global", "iss": "test"}

        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = test_payload

            with pytest.raises(InvalidUserIdException):
                await get_user_from_token("token", async_session)

    @pytest.mark.asyncio
    async def test_get_user_from_token_none_sub(self, async_session: AsyncSession):
        """Test that None sub claim raises InvalidUserIdException."""
        test_payload = {"sub": None, "scope": "global", "iss": "test"}

        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = test_payload

            with pytest.raises(InvalidUserIdException):
                await get_user_from_token("token", async_session)

    @pytest.mark.asyncio
    async def test_get_user_from_token_user_not_found(
        self, async_session: AsyncSession
    ):
        """Test that non-existent user raises UserNotFoundException."""
        non_existent_id = uuid7()
        test_payload = {"sub": str(non_existent_id), "scope": "global", "iss": "test"}

        with patch(
            "app.logic.deps.verify_token", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = test_payload

            with pytest.raises(UserNotFoundException):
                await get_user_from_token("token", async_session)


class TestCheckSuperuserPrivileges:
    """Test suite for check_superuser_privileges function."""

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

    def test_check_superuser_privileges_success(self, superuser: UserDetail):
        """Test that superuser passes privilege check."""
        # Should not raise an exception
        check_superuser_privileges(superuser)

    def test_check_superuser_privileges_regular_user(self, regular_user: UserDetail):
        """Test that regular user fails privilege check."""
        with pytest.raises(InsufficientPrivilegesException) as exc_info:
            check_superuser_privileges(regular_user)

        assert exc_info.value.required_privilege == "superuser"
        assert exc_info.value.user_id == regular_user.id

    def test_check_superuser_privileges_false_flag(self, creator_id):
        """Test that user with is_superuser=False fails check."""
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

        with pytest.raises(InsufficientPrivilegesException):
            check_superuser_privileges(user)

    def test_check_superuser_privileges_empty_meta(self, creator_id):
        """Test that user with empty meta fails check."""
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
            meta={},  # Empty dict instead of None
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        with pytest.raises(InsufficientPrivilegesException):
            check_superuser_privileges(user)

    def test_check_superuser_privileges_missing_flag(self, creator_id):
        """Test that user without is_superuser flag in meta fails check."""
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

        with pytest.raises(InsufficientPrivilegesException):
            check_superuser_privileges(user)


class TestCheckSystemUserRole:
    """Test suite for check_system_user_role function."""

    def test_check_system_user_role_system_user(self, creator_id):
        """Test that SYSTEM_USER role passes the check."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="systemuser",
            primary_email="systemuser@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        # Should not raise an exception
        check_system_user_role(user)

    def test_check_system_user_role_system_admin(self, creator_id):
        """Test that SYSTEM_ADMIN role passes the check."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="systemadmin",
            primary_email="systemadmin@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="Admin",
            name_suffix=None,
            display_name="System Admin",
            default_locale="en",
            system_role=SystemRole.SYSTEM_ADMIN,
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        # Should not raise an exception
        check_system_user_role(user)

    def test_check_system_user_role_system_root(self, creator_id):
        """Test that SYSTEM_ROOT role passes the check."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="systemroot",
            primary_email="systemroot@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="Root",
            name_suffix=None,
            display_name="System Root",
            default_locale="en",
            system_role=SystemRole.SYSTEM_ROOT,
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        # Should not raise an exception
        check_system_user_role(user)

    def test_check_system_user_role_system(self, creator_id):
        """Test that SYSTEM role passes the check."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="system",
            primary_email="system@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="Account",
            name_suffix=None,
            display_name="System Account",
            default_locale="en",
            system_role=SystemRole.SYSTEM,
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        # Should not raise an exception
        check_system_user_role(user)

    def test_check_system_user_role_system_client_fails(self, creator_id):
        """Test that SYSTEM_CLIENT role fails the check."""
        user_id = uuid7()
        now = datetime.now()
        user = UserDetail(
            id=user_id,
            scope="global",
            username="systemclient",
            primary_email="systemclient@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="Client",
            name_suffix=None,
            display_name="System Client",
            default_locale="en",
            system_role=SystemRole.SYSTEM_CLIENT,
            meta={},
            created=now,
            created_by=creator_id,
            last_modified=now,
            last_modified_by=creator_id,
        )

        with pytest.raises(InsufficientPrivilegesException) as exc_info:
            check_system_user_role(user)

        assert exc_info.value.required_privilege == "system user or higher"
        assert exc_info.value.user_id == user.id
