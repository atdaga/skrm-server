"""Unit tests for FIDO2 authentication logic layer."""

import base64
import secrets
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest

from app.core.exceptions.domain_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
)
from app.logic.auth import (
    begin_fido2_authentication,
    begin_fido2_registration,
    complete_fido2_authentication,
    complete_fido2_registration,
    delete_credential,
    list_user_credentials,
    perform_2fa_login,
    perform_passwordless_login,
    update_credential_nickname,
)
from app.models.k_fido2_credential import KFido2Credential
from app.models.k_principal import KPrincipal


@pytest.fixture
async def test_user(async_session, creator_id):
    """Create a test user for FIDO2 operations."""
    user_id = uuid7()

    # Create a creator principal if needed
    creator_principal = KPrincipal(
        id=creator_id,
        scope="global",
        username="creator",
        primary_email="creator@example.com",
        primary_email_verified=True,
        primary_phone=None,
        primary_phone_verified=False,
        human=True,
        enabled=True,
        time_zone="UTC",
        name_prefix=None,
        first_name="Creator",
        middle_name=None,
        last_name="User",
        name_suffix=None,
        display_name="Creator User",
        default_locale="en",
        system_role="system_user",
        meta={},
        created=datetime.now(),
        created_by=creator_id,
        last_modified=datetime.now(),
        last_modified_by=creator_id,
    )
    async_session.add(creator_principal)
    await async_session.commit()

    user = KPrincipal(
        id=user_id,
        scope="global",
        username="testuser",
        primary_email="test@example.com",
        primary_email_verified=True,
        primary_phone=None,
        primary_phone_verified=False,
        human=True,
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
        created=datetime.now(),
        created_by=creator_id,
        last_modified=datetime.now(),
        last_modified_by=creator_id,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
def mock_credential(creator_id):
    """Create a mock FIDO2 credential."""
    user_id = uuid7()
    return KFido2Credential(
        id=uuid7(),
        principal_id=user_id,
        credential_id=secrets.token_bytes(32),
        public_key=secrets.token_bytes(65),
        sign_count=0,
        aaguid=bytes.fromhex("00112233445566778899aabbccddeeff"),
        transports=["usb"],
        is_discoverable=False,
        nickname="Test Key",
        last_used=None,
        created=datetime.now(),
        created_by=creator_id,
        last_modified=datetime.now(),
        last_modified_by=creator_id,
    )


class TestBeginFido2Registration:
    """Test suite for begin_fido2_registration function."""

    @pytest.mark.asyncio
    async def test_begin_registration_success(self, async_session, test_user):
        """Test successful registration initiation."""
        with patch("app.logic.auth.get_fido2_server") as mock_server:
            # Mock the server response
            mock_server_instance = MagicMock()
            mock_registration_data = MagicMock()
            mock_registration_data.rp = {"id": "localhost", "name": "Test"}
            mock_registration_data.user = {
                "id": str(test_user.id).encode("utf-8"),
                "name": "testuser",
                "displayName": "Test User",
            }
            mock_registration_data.challenge = secrets.token_bytes(32)
            mock_registration_data.pub_key_cred_params = []
            mock_registration_data.timeout = 60000
            mock_registration_data.exclude_credentials = []
            mock_registration_data.authenticator_selection = None
            mock_registration_data.attestation = "none"

            mock_state = {"challenge": secrets.token_bytes(32)}
            mock_server_instance.register_begin.return_value = (
                mock_registration_data,
                mock_state,
            )
            mock_server.return_value = mock_server_instance

            response, session_id = await begin_fido2_registration(
                test_user.id, async_session
            )

            assert response is not None
            assert session_id is not None
            assert "publicKey" in response.model_dump()

    @pytest.mark.asyncio
    async def test_begin_registration_user_not_found(self, async_session):
        """Test registration fails when user not found."""
        nonexistent_user_id = uuid7()

        with pytest.raises(InvalidCredentialsException):
            await begin_fido2_registration(nonexistent_user_id, async_session)

    @pytest.mark.asyncio
    async def test_begin_registration_excludes_existing_credentials(
        self, async_session, test_user, mock_credential
    ):
        """Test that existing credentials are excluded from registration."""
        # Add credential
        mock_credential.principal_id = test_user.id
        async_session.add(mock_credential)
        await async_session.commit()

        with patch("app.logic.auth.get_fido2_server") as mock_server:
            mock_server_instance = MagicMock()
            mock_registration_data = MagicMock()
            mock_registration_data.rp = {"id": "localhost", "name": "Test"}
            mock_registration_data.user = {"id": b"test", "name": "test"}
            mock_registration_data.challenge = secrets.token_bytes(32)
            mock_registration_data.pub_key_cred_params = []
            mock_registration_data.timeout = 60000
            mock_registration_data.exclude_credentials = []
            mock_registration_data.authenticator_selection = None
            mock_registration_data.attestation = "none"

            mock_server_instance.register_begin.return_value = (
                mock_registration_data,
                {"challenge": secrets.token_bytes(32)},
            )
            mock_server.return_value = mock_server_instance

            response, session_id = await begin_fido2_registration(
                test_user.id, async_session
            )

            # Verify register_begin was called with credentials to exclude
            call_args = mock_server_instance.register_begin.call_args
            assert "credentials" in call_args[1]


class TestCompleteFido2Registration:
    """Test suite for complete_fido2_registration function."""

    @pytest.mark.asyncio
    async def test_complete_registration_invalid_session(
        self, async_session, test_user
    ):
        """Test registration fails with invalid session."""
        attestation_response = {
            "id": base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode()
            .rstrip("="),
            "response": {
                "clientDataJSON": base64.urlsafe_b64encode(b"{}").decode(),
                "attestationObject": base64.urlsafe_b64encode(b"test").decode(),
            },
        }

        with pytest.raises(InvalidTokenException):
            await complete_fido2_registration(
                test_user.id,
                "invalid_session",
                attestation_response,
                "Test Key",
                async_session,
            )

    @pytest.mark.asyncio
    async def test_complete_registration_success(self, async_session, test_user):
        """Test successful registration completion."""
        from app.core.fido2_server import store_challenge

        session_id = "test_session"
        challenge = secrets.token_bytes(32)
        store_challenge(session_id, challenge)

        # Mock the FIDO2 server verification
        with patch("app.logic.auth.get_fido2_server") as mock_server:
            # Create mock objects
            mock_auth_data = MagicMock()

            # Mock credential data
            mock_credential_data = MagicMock()
            mock_credential_data.credential_id = secrets.token_bytes(32)
            mock_credential_data.public_key = secrets.token_bytes(65)
            mock_credential_data.aaguid = bytes.fromhex(
                "00112233445566778899aabbccddeeff"
            )

            mock_auth_data.credential_data = mock_credential_data
            mock_auth_data.counter = 0
            mock_auth_data.flags = 0x04  # User verified flag

            mock_server_instance = MagicMock()
            mock_server_instance.register_complete.return_value = mock_auth_data

            mock_server.return_value = mock_server_instance

            # RegistrationResponse requires an "id" field
            credential_id_b64 = (
                base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
            )
            attestation_response = {
                "id": credential_id_b64,
                "response": {
                    "clientDataJSON": base64.urlsafe_b64encode(b"{}").decode(),
                    "attestationObject": base64.urlsafe_b64encode(b"test").decode(),
                    "transports": ["usb"],
                },
            }

            credential_id = await complete_fido2_registration(
                test_user.id, session_id, attestation_response, "My Key", async_session
            )

            assert credential_id is not None
            assert isinstance(credential_id, str)

            # Verify register_complete was called with correct parameters
            mock_server_instance.register_complete.assert_called_once()
            call_args = mock_server_instance.register_complete.call_args
            assert "state" in call_args.kwargs
            assert "response" in call_args.kwargs
            # Verify state has websafe-encoded challenge
            state = call_args.kwargs["state"]
            assert "challenge" in state
            assert isinstance(state["challenge"], str)  # websafe-encoded string
            assert "user_verification" in state
            # Verify response is passed as-is
            assert call_args.kwargs["response"] == attestation_response


class TestBeginFido2Authentication:
    """Test suite for begin_fido2_authentication function."""

    @pytest.mark.asyncio
    async def test_begin_authentication_with_username(
        self, async_session, test_user, mock_credential
    ):
        """Test authentication initiation with username."""
        mock_credential.principal_id = test_user.id
        async_session.add(mock_credential)
        await async_session.commit()

        with patch("app.logic.auth.get_fido2_server") as mock_server:
            mock_server_instance = MagicMock()
            mock_auth_data = MagicMock()
            mock_auth_data.challenge = secrets.token_bytes(32)
            mock_auth_data.timeout = 60000
            mock_auth_data.rp_id = "localhost"
            mock_auth_data.allow_credentials = []
            mock_auth_data.user_verification = "preferred"

            mock_server_instance.authenticate_begin.return_value = (
                mock_auth_data,
                {"challenge": secrets.token_bytes(32)},
            )
            mock_server.return_value = mock_server_instance

            response, session_id = await begin_fido2_authentication(
                test_user.username, False, async_session
            )

            assert response is not None
            assert session_id is not None
            assert "publicKey" in response.model_dump()

    @pytest.mark.asyncio
    async def test_begin_authentication_passwordless(self, async_session):
        """Test passwordless authentication (no username)."""
        with patch("app.logic.auth.get_fido2_server") as mock_server:
            mock_server_instance = MagicMock()
            mock_auth_data = MagicMock()
            mock_auth_data.challenge = secrets.token_bytes(32)
            mock_auth_data.timeout = 60000
            mock_auth_data.rp_id = "localhost"
            mock_auth_data.allow_credentials = []
            mock_auth_data.user_verification = "preferred"

            mock_server_instance.authenticate_begin.return_value = (
                mock_auth_data,
                {"challenge": secrets.token_bytes(32)},
            )
            mock_server.return_value = mock_server_instance

            response, session_id = await begin_fido2_authentication(
                None, False, async_session
            )

            assert response is not None
            assert session_id is not None


class TestCompleteFido2Authentication:
    """Test suite for complete_fido2_authentication function."""

    @pytest.mark.asyncio
    async def test_complete_authentication_invalid_session(self, async_session):
        """Test authentication fails with invalid session."""
        assertion_response = {"id": "test", "response": {}}

        with pytest.raises(InvalidTokenException):
            await complete_fido2_authentication(
                "invalid_session", assertion_response, async_session
            )

    @pytest.mark.asyncio
    async def test_complete_authentication_credential_not_found(self, async_session):
        """Test authentication fails when credential not found."""
        from app.core.fido2_server import store_challenge

        session_id = "test_session"
        challenge = secrets.token_bytes(32)
        store_challenge(session_id, challenge)

        credential_id_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        assertion_response = {"id": credential_id_b64, "response": {}}

        # Should raise InvalidCredentialsException which is caught and re-raised as InvalidTokenException
        with pytest.raises((InvalidCredentialsException, InvalidTokenException)):
            await complete_fido2_authentication(
                session_id, assertion_response, async_session
            )


class TestPerformPasswordlessLogin:
    """Test suite for perform_passwordless_login function."""

    @pytest.mark.asyncio
    async def test_passwordless_login_success(self, async_session, test_user):
        """Test successful passwordless login."""
        with patch(
            "app.logic.auth.complete_fido2_authentication", new_callable=AsyncMock
        ) as mock_complete, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_credential = MagicMock()
            mock_complete.return_value = (test_user, mock_credential)
            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"

            result = await perform_passwordless_login(
                "session_id", {"id": "test"}, async_session
            )

            assert result.access_token == "access_token"
            assert result.refresh_token == "refresh_token"
            assert result.token_type == "bearer"


class TestPerform2faLogin:
    """Test suite for perform_2fa_login function."""

    @pytest.mark.asyncio
    async def test_2fa_login_success(self, async_session, test_user):
        """Test successful 2FA login."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.complete_fido2_authentication", new_callable=AsyncMock
        ) as mock_fido2, patch(
            "app.logic.auth.create_access_token", new_callable=AsyncMock
        ) as mock_access, patch(
            "app.logic.auth.create_refresh_token", new_callable=AsyncMock
        ) as mock_refresh:
            mock_credential = MagicMock()
            mock_auth.return_value = test_user
            mock_fido2.return_value = (test_user, mock_credential)
            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"

            result = await perform_2fa_login(
                "testuser", "password", "session_id", {"id": "test"}, async_session
            )

            assert result.access_token == "access_token"
            assert result.refresh_token == "refresh_token"

    @pytest.mark.asyncio
    async def test_2fa_login_password_fails(self, async_session):
        """Test 2FA login fails with invalid password."""
        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = None

            with pytest.raises(InvalidCredentialsException):
                await perform_2fa_login(
                    "testuser",
                    "wrongpassword",
                    "session_id",
                    {"id": "test"},
                    async_session,
                )

    @pytest.mark.asyncio
    async def test_2fa_login_user_mismatch(self, async_session):
        """Test 2FA login fails when FIDO2 credential belongs to different user."""
        user1_id = uuid7()
        user2_id = uuid7()

        user1 = MagicMock()
        user1.id = user1_id

        user2 = MagicMock()
        user2.id = user2_id

        with patch(
            "app.logic.auth.authenticate_user", new_callable=AsyncMock
        ) as mock_auth, patch(
            "app.logic.auth.complete_fido2_authentication", new_callable=AsyncMock
        ) as mock_fido2:
            mock_auth.return_value = user1
            mock_fido2.return_value = (user2, MagicMock())

            with pytest.raises(InvalidCredentialsException):
                await perform_2fa_login(
                    "testuser",
                    "password",
                    "session_id",
                    {"id": "test"},
                    async_session,
                )


class TestListUserCredentials:
    """Test suite for list_user_credentials function."""

    @pytest.mark.asyncio
    async def test_list_empty_credentials(self, async_session, test_user):
        """Test listing credentials when user has none."""
        credentials = await list_user_credentials(test_user.id, async_session)

        assert credentials == []

    @pytest.mark.asyncio
    async def test_list_multiple_credentials(
        self, async_session, test_user, creator_id
    ):
        """Test listing multiple credentials."""
        # Create multiple credentials
        for i in range(3):
            credential = KFido2Credential(
                principal_id=test_user.id,
                credential_id=secrets.token_bytes(32),
                public_key=secrets.token_bytes(65),
                sign_count=i,
                aaguid=bytes.fromhex("00112233445566778899aabbccddeeff"),
                transports=["usb"],
                nickname=f"Key {i}",
                created=datetime.now(),
                created_by=creator_id,
                last_modified=datetime.now(),
                last_modified_by=creator_id,
            )
            async_session.add(credential)

        await async_session.commit()

        credentials = await list_user_credentials(test_user.id, async_session)

        assert len(credentials) == 3
        assert all(c.nickname.startswith("Key") for c in credentials)


class TestUpdateCredentialNickname:
    """Test suite for update_credential_nickname function."""

    @pytest.mark.asyncio
    async def test_update_nickname_success(
        self, async_session, test_user, mock_credential
    ):
        """Test successful nickname update."""
        mock_credential.principal_id = test_user.id
        async_session.add(mock_credential)
        await async_session.commit()

        await update_credential_nickname(
            test_user.id, mock_credential.id, "New Nickname", async_session
        )

        await async_session.refresh(mock_credential)
        assert mock_credential.nickname == "New Nickname"

    @pytest.mark.asyncio
    async def test_update_nickname_not_found(self, async_session, test_user):
        """Test update fails when credential not found."""
        with pytest.raises(InvalidCredentialsException):
            await update_credential_nickname(
                test_user.id, uuid7(), "New Nickname", async_session
            )

    @pytest.mark.asyncio
    async def test_update_nickname_wrong_user(
        self, async_session, test_user, mock_credential, creator_id
    ):
        """Test update fails when credential belongs to different user."""
        other_user_id = uuid7()
        other_user = KPrincipal(
            id=other_user_id,
            scope="global",
            username="otheruser",
            primary_email="other@example.com",
            primary_email_verified=False,
            primary_phone=None,
            primary_phone_verified=False,
            human=True,
            enabled=True,
            time_zone="UTC",
            first_name="Other",
            last_name="User",
            display_name="Other User",
            default_locale="en",
            system_role="system_user",
            meta={},
            created=datetime.now(),
            created_by=creator_id,
            last_modified=datetime.now(),
            last_modified_by=creator_id,
        )

        async_session.add(other_user)
        await async_session.commit()

        mock_credential.principal_id = other_user_id
        async_session.add(mock_credential)
        await async_session.commit()

        with pytest.raises(InvalidCredentialsException):
            await update_credential_nickname(
                test_user.id, mock_credential.id, "New Nickname", async_session
            )


class TestDeleteCredential:
    """Test suite for delete_credential function."""

    @pytest.mark.asyncio
    async def test_delete_credential_success(
        self, async_session, test_user, mock_credential
    ):
        """Test successful credential deletion."""
        mock_credential.principal_id = test_user.id
        async_session.add(mock_credential)
        await async_session.commit()

        await delete_credential(test_user.id, mock_credential.id, async_session)

        # Verify credential was soft-deleted
        from sqlalchemy import select

        result = await async_session.execute(
            select(KFido2Credential).where(KFido2Credential.id == mock_credential.id)
        )
        deleted_credential = result.scalar_one_or_none()
        assert deleted_credential is not None
        assert deleted_credential.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_credential_not_found(self, async_session, test_user):
        """Test delete fails when credential not found."""
        with pytest.raises(InvalidCredentialsException):
            await delete_credential(test_user.id, uuid7(), async_session)

    @pytest.mark.asyncio
    async def test_delete_credential_wrong_user(
        self, async_session, test_user, mock_credential, creator_id
    ):
        """Test delete fails when credential belongs to different user."""
        other_user_id = uuid7()
        other_user = KPrincipal(
            id=other_user_id,
            scope="global",
            username="otheruser",
            primary_email="other@example.com",
            primary_email_verified=False,
            primary_phone=None,
            primary_phone_verified=False,
            human=True,
            enabled=True,
            time_zone="UTC",
            first_name="Other",
            last_name="User",
            display_name="Other User",
            default_locale="en",
            system_role="system_user",
            meta={},
            created=datetime.now(),
            created_by=creator_id,
            last_modified=datetime.now(),
            last_modified_by=creator_id,
        )

        async_session.add(other_user)
        await async_session.commit()

        mock_credential.principal_id = other_user_id
        async_session.add(mock_credential)
        await async_session.commit()

        with pytest.raises(InvalidCredentialsException):
            await delete_credential(test_user.id, mock_credential.id, async_session)
