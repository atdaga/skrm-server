"""Unit tests for FIDO2 authentication endpoints."""

import base64
import secrets
from datetime import datetime
from unittest.mock import ANY, AsyncMock, patch
from uuid import uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.auth import router
from app.routes.deps import get_current_user
from app.schemas.fido2 import (
    Fido2AuthenticationBeginResponse,
    Fido2CredentialDetail,
    Fido2RegistrationBeginResponse,
)
from app.schemas.user import Token, UserDetail


@pytest.fixture
def app(app, mock_user: UserDetail) -> FastAPI:
    """Create a FastAPI app with auth router and dependency overrides."""
    app.include_router(router)

    # Override the authentication dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return app


@pytest.fixture
def app_without_auth(app_without_auth):
    """Create a FastAPI app without authentication overrides for testing auth failures."""
    app_without_auth.include_router(router)
    return app_without_auth


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing with authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestFido2RegisterBeginEndpoint:
    """Test suite for POST /auth/fido2/register/begin endpoint."""

    @pytest.mark.asyncio
    async def test_register_begin_success(self, client: AsyncClient):
        """Test successful registration initiation."""
        with patch(
            "app.logic.auth.begin_fido2_registration", new_callable=AsyncMock
        ) as mock_begin:
            challenge_bytes = secrets.token_bytes(32)
            challenge_b64 = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8")
            response = Fido2RegistrationBeginResponse(
                publicKey={
                    "challenge": challenge_b64,
                    "rp": {"id": "localhost", "name": "Test"},
                    "user": {"id": "test", "name": "testuser"},
                }
            )
            session_id = "test_session_123"
            mock_begin.return_value = (response, session_id)

            result = await client.post("/auth/fido2/register/begin")

            assert result.status_code == 200
            data = result.json()
            assert "publicKey" in data
            assert "sessionId" in data["publicKey"]

    @pytest.mark.asyncio
    async def test_register_begin_unauthorized(self, client_no_auth: AsyncClient):
        """Test registration fails without authentication."""
        result = await client_no_auth.post("/auth/fido2/register/begin")
        assert result.status_code == 401


class TestFido2RegisterCompleteEndpoint:
    """Test suite for POST /auth/fido2/register/complete endpoint."""

    @pytest.mark.asyncio
    async def test_register_complete_success(self, client: AsyncClient, mock_user):
        """Test successful registration completion."""
        with patch(
            "app.logic.auth.complete_fido2_registration", new_callable=AsyncMock
        ) as mock_complete:
            mock_complete.return_value = "test_credential_id_base64"

            result = await client.post(
                "/auth/fido2/register/complete",
                json={
                    "credential": {
                        "id": "test_id",
                        "response": {
                            "clientDataJSON": "test",
                            "attestationObject": "test",
                        },
                    },
                    "nickname": "My YubiKey",
                    "session_id": "test_session",
                },
            )

            assert result.status_code == 200
            data = result.json()
            assert data["credential_id"] == "test_credential_id_base64"
            assert "message" in data

            mock_complete.assert_called_once_with(
                mock_user.id, "test_session", ANY, "My YubiKey", ANY
            )


class TestFido2AuthenticateBeginEndpoint:
    """Test suite for POST /auth/fido2/authenticate/begin endpoint."""

    @pytest.mark.asyncio
    async def test_authenticate_begin_with_username(self, client: AsyncClient):
        """Test authentication initiation with username."""
        with patch(
            "app.logic.auth.begin_fido2_authentication", new_callable=AsyncMock
        ) as mock_begin:
            challenge_bytes = secrets.token_bytes(32)
            challenge_b64 = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8")
            response = Fido2AuthenticationBeginResponse(
                publicKey={
                    "challenge": challenge_b64,
                    "rpId": "localhost",
                    "allowCredentials": [],
                }
            )
            session_id = "test_session_456"
            mock_begin.return_value = (response, session_id)

            result = await client.post(
                "/auth/fido2/authenticate/begin",
                json={"username": "testuser", "require_user_verification": False},
            )

            assert result.status_code == 200
            data = result.json()
            assert "publicKey" in data
            assert "sessionId" in data["publicKey"]

            mock_begin.assert_called_once_with("testuser", False, ANY)

    @pytest.mark.asyncio
    async def test_authenticate_begin_passwordless(self, client: AsyncClient):
        """Test passwordless authentication (no username)."""
        with patch(
            "app.logic.auth.begin_fido2_authentication", new_callable=AsyncMock
        ) as mock_begin:
            challenge_bytes = secrets.token_bytes(32)
            challenge_b64 = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8")
            response = Fido2AuthenticationBeginResponse(
                publicKey={
                    "challenge": challenge_b64,
                    "rpId": "localhost",
                    "allowCredentials": [],
                }
            )
            session_id = "test_session_789"
            mock_begin.return_value = (response, session_id)

            result = await client.post(
                "/auth/fido2/authenticate/begin",
                json={"username": None, "require_user_verification": False},
            )

            assert result.status_code == 200
            mock_begin.assert_called_once_with(None, False, ANY)


class TestFido2AuthenticateCompleteEndpoint:
    """Test suite for POST /auth/fido2/authenticate/complete endpoint."""

    @pytest.mark.asyncio
    async def test_authenticate_complete_success(self, client: AsyncClient):
        """Test successful passwordless authentication."""
        with patch(
            "app.logic.auth.perform_passwordless_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            result = await client.post(
                "/auth/fido2/authenticate/complete",
                json={
                    "credential": {
                        "id": "test_id",
                        "response": {
                            "clientDataJSON": "test",
                            "authenticatorData": "test",
                            "signature": "test",
                        },
                    },
                    "session_id": "test_session",
                },
            )

            assert result.status_code == 200
            data = result.json()
            assert data["access_token"] == "test_access_token"
            assert data["token_type"] == "bearer"
            # For web clients, refresh_token is in cookie, not response body
            assert data["refresh_token"] is None
            # Verify refresh token cookie is set
            assert "refresh_token" in result.cookies
            assert result.cookies["refresh_token"] == "test_refresh_token"

    @pytest.mark.asyncio
    async def test_authenticate_complete_invalid_credentials(self, client: AsyncClient):
        """Test authentication fails with invalid credentials."""
        from app.core.exceptions.domain_exceptions import InvalidCredentialsException

        with patch(
            "app.logic.auth.perform_passwordless_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.side_effect = InvalidCredentialsException(username="test")

            result = await client.post(
                "/auth/fido2/authenticate/complete",
                json={
                    "credential": {"id": "test", "response": {}},
                    "session_id": "test_session",
                },
            )

            assert result.status_code == 401


class TestLogin2faEndpoint:
    """Test suite for POST /auth/login/2fa endpoint."""

    @pytest.mark.asyncio
    async def test_login_2fa_success(self, client: AsyncClient):
        """Test successful 2FA login."""
        with patch(
            "app.logic.auth.perform_2fa_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.return_value = Token(
                access_token="test_access_token",
                token_type="bearer",
                refresh_token="test_refresh_token",
            )

            result = await client.post(
                "/auth/login/2fa",
                json={
                    "username": "testuser",
                    "password": "testpassword",
                    "session_id": "test_session",
                    "credential": {"id": "test", "response": {}},
                },
            )

            assert result.status_code == 200
            data = result.json()
            assert data["access_token"] == "test_access_token"
            # For web clients, refresh_token is in cookie, not response body
            assert data["refresh_token"] is None
            # Verify refresh token cookie is set
            assert "refresh_token" in result.cookies
            assert result.cookies["refresh_token"] == "test_refresh_token"

            mock_login.assert_called_once_with(
                "testuser", "testpassword", "test_session", ANY, ANY
            )

    @pytest.mark.asyncio
    async def test_login_2fa_invalid_password(self, client: AsyncClient):
        """Test 2FA login fails with invalid password."""
        from app.core.exceptions.domain_exceptions import InvalidCredentialsException

        with patch(
            "app.logic.auth.perform_2fa_login", new_callable=AsyncMock
        ) as mock_login:
            mock_login.side_effect = InvalidCredentialsException(username="testuser")

            result = await client.post(
                "/auth/login/2fa",
                json={
                    "username": "testuser",
                    "password": "wrongpassword",
                    "session_id": "test_session",
                    "credential": {"id": "test", "response": {}},
                },
            )

            assert result.status_code == 401


class TestListCredentialsEndpoint:
    """Test suite for GET /auth/fido2/credentials endpoint."""

    @pytest.mark.asyncio
    async def test_list_credentials_success(self, client: AsyncClient):
        """Test listing user credentials."""
        with patch(
            "app.logic.auth.list_user_credentials", new_callable=AsyncMock
        ) as mock_list:
            credentials = [
                Fido2CredentialDetail(
                    id=uuid7(),
                    credential_id="test_cred_1",
                    nickname="YubiKey 5",
                    aaguid="00112233445566778899aabbccddeeff",
                    transports=["usb"],
                    is_discoverable=False,
                    last_used=None,
                    created=datetime.now(),
                ),
                Fido2CredentialDetail(
                    id=uuid7(),
                    credential_id="test_cred_2",
                    nickname="iPhone TouchID",
                    aaguid="00112233445566778899aabbccddeeff",
                    transports=["internal"],
                    is_discoverable=True,
                    last_used=datetime.now(),
                    created=datetime.now(),
                ),
            ]
            mock_list.return_value = credentials

            result = await client.get("/auth/fido2/credentials")

            assert result.status_code == 200
            data = result.json()
            assert "credentials" in data
            assert data["total"] == 2
            assert len(data["credentials"]) == 2

    @pytest.mark.asyncio
    async def test_list_credentials_empty(self, client: AsyncClient):
        """Test listing when user has no credentials."""
        with patch(
            "app.logic.auth.list_user_credentials", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            result = await client.get("/auth/fido2/credentials")

            assert result.status_code == 200
            data = result.json()
            assert data["total"] == 0
            assert len(data["credentials"]) == 0


class TestUpdateCredentialEndpoint:
    """Test suite for PATCH /auth/fido2/credentials/{credential_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_credential_success(self, client: AsyncClient, mock_user):
        """Test successful credential update."""
        credential_id = uuid7()

        with (
            patch(
                "app.logic.auth.update_credential_nickname", new_callable=AsyncMock
            ) as mock_update,
            patch(
                "app.logic.auth.list_user_credentials", new_callable=AsyncMock
            ) as mock_list,
        ):
            updated_credential = Fido2CredentialDetail(
                id=credential_id,
                credential_id="test_cred",
                nickname="Updated Nickname",
                aaguid="00112233445566778899aabbccddeeff",
                transports=["usb"],
                is_discoverable=False,
                last_used=None,
                created=datetime.now(),
            )
            mock_list.return_value = [updated_credential]

            result = await client.patch(
                f"/auth/fido2/credentials/{credential_id}",
                json={"nickname": "Updated Nickname"},
            )

            assert result.status_code == 200
            data = result.json()
            assert data["nickname"] == "Updated Nickname"

            mock_update.assert_called_once_with(
                mock_user.id, credential_id, "Updated Nickname", ANY
            )

    @pytest.mark.asyncio
    async def test_update_credential_not_found(self, client: AsyncClient, mock_user):
        """Test update fails when credential not found."""
        from app.core.exceptions.domain_exceptions import InvalidCredentialsException

        credential_id = uuid7()

        with patch(
            "app.logic.auth.update_credential_nickname", new_callable=AsyncMock
        ) as mock_update:
            mock_update.side_effect = InvalidCredentialsException(
                username=str(mock_user.id)
            )

            result = await client.patch(
                f"/auth/fido2/credentials/{credential_id}",
                json={"nickname": "New Name"},
            )

            assert result.status_code == 404


class TestDeleteCredentialEndpoint:
    """Test suite for DELETE /auth/fido2/credentials/{credential_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_credential_success(self, client: AsyncClient, mock_user):
        """Test successful credential deletion."""
        credential_id = uuid7()

        with patch(
            "app.logic.auth.delete_credential", new_callable=AsyncMock
        ) as mock_delete:
            result = await client.delete(f"/auth/fido2/credentials/{credential_id}")

            assert result.status_code == 200
            data = result.json()
            assert "message" in data

            mock_delete.assert_called_once_with(
                mock_user.id, credential_id, ANY, hard_delete=False
            )

    @pytest.mark.asyncio
    async def test_delete_credential_not_found(self, client: AsyncClient, mock_user):
        """Test delete fails when credential not found."""
        from app.core.exceptions.domain_exceptions import InvalidCredentialsException

        credential_id = uuid7()

        with patch(
            "app.logic.auth.delete_credential", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.side_effect = InvalidCredentialsException(
                username=str(mock_user.id)
            )

            result = await client.delete(f"/auth/fido2/credentials/{credential_id}")

            assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_credential_unauthorized(self, client_no_auth: AsyncClient):
        """Test delete fails without authentication."""
        credential_id = uuid7()
        result = await client_no_auth.delete(f"/auth/fido2/credentials/{credential_id}")
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_hard_delete_credential_success(
        self, async_session, mock_system_root_user, mock_token_data
    ):
        """Test hard deleting credential with system root privileges."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.auth import oauth2_scheme
        from app.core.db.database import get_db
        from app.models import KFido2Credential, KPrincipal
        from app.routes.auth import router
        from app.routes.deps import get_current_token, get_current_user

        # Create app with system root overrides
        app = FastAPI()
        app.include_router(router)

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

        # Create principal and credential
        principal = KPrincipal(
            id=mock_system_root_user.id,
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=mock_system_root_user.id,
            last_modified_by=mock_system_root_user.id,
        )
        async_session.add(principal)
        await async_session.commit()

        credential = KFido2Credential(
            principal_id=mock_system_root_user.id,
            credential_id=b"test_cred_id",
            public_key=b"test_public_key",
            sign_count=0,
            aaguid=b"test_aaguid_bytes",
            created_by=mock_system_root_user.id,
            last_modified_by=mock_system_root_user.id,
        )
        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)
        cred_id = credential.id

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            result = await client.delete(
                f"/auth/fido2/credentials/{cred_id}?hard_delete=true"
            )

        assert result.status_code == 200

        # Verify hard deleted
        from sqlalchemy import select

        result = await async_session.execute(
            select(KFido2Credential).where(KFido2Credential.id == cred_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_hard_delete_credential_forbidden(self, client: AsyncClient):
        """Test hard delete is forbidden for regular users."""
        credential_id = uuid7()

        result = await client.delete(
            f"/auth/fido2/credentials/{credential_id}?hard_delete=true"
        )

        assert result.status_code == 403
