"""Unit tests for KFido2Credential model."""

import secrets
from datetime import datetime
from uuid import uuid7

import pytest

from app.models.k_fido2_credential import KFido2Credential
from app.models.k_principal import KPrincipal


class TestKFido2CredentialModel:
    """Test suite for KFido2Credential model."""

    @pytest.fixture
    def test_principal(self, creator_id):
        """Create a test principal for foreign key relationships."""
        return KPrincipal(
            id=uuid7(),
            scope="global",
            username="testuser",
            primary_email="test@example.com",
            primary_email_verified=False,
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

    @pytest.mark.asyncio
    async def test_create_fido2_credential(self, async_session, test_principal):
        """Test creating a new FIDO2 credential."""
        # First create the principal
        async_session.add(test_principal)
        await async_session.commit()

        now = datetime.now()
        credential = KFido2Credential(
            principal_id=test_principal.id,
            credential_id=secrets.token_bytes(32),
            public_key=secrets.token_bytes(65),
            sign_count=0,
            aaguid=bytes.fromhex("00112233445566778899aabbccddeeff"),
            transports=["usb", "nfc"],
            is_discoverable=False,
            nickname="My YubiKey",
            last_used=None,
            created=now,
            created_by=test_principal.id,
            last_modified=now,
            last_modified_by=test_principal.id,
        )

        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.id is not None
        assert credential.principal_id == test_principal.id
        assert len(credential.credential_id) == 32
        assert credential.sign_count == 0
        assert credential.nickname == "My YubiKey"
        assert credential.transports == ["usb", "nfc"]

    @pytest.mark.asyncio
    async def test_credential_defaults(self, async_session, test_principal):
        """Test default values for optional fields."""
        async_session.add(test_principal)
        await async_session.commit()

        now = datetime.now()
        credential = KFido2Credential(
            principal_id=test_principal.id,
            credential_id=secrets.token_bytes(32),
            public_key=secrets.token_bytes(65),
            sign_count=0,
            aaguid=bytes.fromhex("00112233445566778899aabbccddeeff"),
            created=now,
            created_by=test_principal.id,
            last_modified=now,
            last_modified_by=test_principal.id,
        )

        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.transports == []
        assert credential.is_discoverable is False
        assert credential.nickname is None
        assert credential.last_used is None

    @pytest.mark.asyncio
    async def test_update_sign_count(self, async_session, test_principal):
        """Test updating sign count."""
        async_session.add(test_principal)
        await async_session.commit()

        now = datetime.now()
        credential = KFido2Credential(
            principal_id=test_principal.id,
            credential_id=secrets.token_bytes(32),
            public_key=secrets.token_bytes(65),
            sign_count=0,
            aaguid=bytes.fromhex("00112233445566778899aabbccddeeff"),
            created=now,
            created_by=test_principal.id,
            last_modified=now,
            last_modified_by=test_principal.id,
        )

        async_session.add(credential)
        await async_session.commit()

        # Update sign count
        credential.sign_count = 5
        credential.last_used = datetime.now()
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.sign_count == 5
        assert credential.last_used is not None

    @pytest.mark.asyncio
    async def test_update_nickname(self, async_session, test_principal):
        """Test updating credential nickname."""
        async_session.add(test_principal)
        await async_session.commit()

        now = datetime.now()
        credential = KFido2Credential(
            principal_id=test_principal.id,
            credential_id=secrets.token_bytes(32),
            public_key=secrets.token_bytes(65),
            sign_count=0,
            aaguid=bytes.fromhex("00112233445566778899aabbccddeeff"),
            nickname="Old Name",
            created=now,
            created_by=test_principal.id,
            last_modified=now,
            last_modified_by=test_principal.id,
        )

        async_session.add(credential)
        await async_session.commit()

        credential.nickname = "New Name"
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.nickname == "New Name"
