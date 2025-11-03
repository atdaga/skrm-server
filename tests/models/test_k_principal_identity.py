"""Unit tests for KPrincipalIdentity model."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_principal import KPrincipal
from app.models.k_principal_identity import KPrincipalIdentity


class TestKPrincipalIdentityModel:
    """Test suite for KPrincipalIdentity model."""

    @pytest.fixture
    async def principal(self, session: AsyncSession, creator_id: UUID) -> KPrincipal:
        """Create a test principal."""
        principal = KPrincipal(
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(principal)
        await session.commit()
        await session.refresh(principal)
        return principal

    @pytest.mark.asyncio
    async def test_create_identity_with_required_fields(self, session: AsyncSession, creator_id: UUID):
        """Test creating an identity with only required fields."""
        identity = KPrincipalIdentity(
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.id is not None
        assert isinstance(identity.id, UUID)
        assert identity.principal_id is None
        assert identity.password is None
        assert identity.public_key is None
        assert identity.device_id is None
        assert identity.expires is None

    @pytest.mark.asyncio
    async def test_identity_default_values(self, session: AsyncSession, creator_id: UUID):
        """Test that default values are set correctly."""
        identity = KPrincipalIdentity(
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.details == {}
        assert isinstance(identity.created, datetime)
        assert isinstance(identity.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_identity_with_password(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test creating an identity with a password hash."""
        password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7N0n8VqN.K"

        identity = KPrincipalIdentity(
            principal_id=principal.id,
            password=password_hash,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.principal_id == principal.id
        assert identity.password == password_hash

    @pytest.mark.asyncio
    async def test_identity_with_public_key(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test creating an identity with a public key."""
        public_key = b"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ..."

        identity = KPrincipalIdentity(
            principal_id=principal.id,
            public_key=public_key,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.public_key == public_key

    @pytest.mark.asyncio
    async def test_identity_with_device_id(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test creating an identity with a device ID."""
        device_id = "mobile-device-12345"

        identity = KPrincipalIdentity(
            principal_id=principal.id,
            device_id=device_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.device_id == device_id

    @pytest.mark.asyncio
    async def test_identity_with_expiration(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test creating an identity with an expiration date."""
        expiration = datetime.now() + timedelta(days=30)

        identity = KPrincipalIdentity(
            principal_id=principal.id,
            expires=expiration,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.expires is not None
        assert isinstance(identity.expires, datetime)

    @pytest.mark.asyncio
    async def test_identity_with_all_fields(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test creating an identity with all fields populated."""
        password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7N0n8VqN.K"
        public_key = b"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ..."
        device_id = "mobile-device-12345"
        expiration = datetime.now() + timedelta(days=30)
        details = {"auth_method": "password", "last_login": "2024-01-01T00:00:00Z"}

        identity = KPrincipalIdentity(
            principal_id=principal.id,
            password=password_hash,
            public_key=public_key,
            device_id=device_id,
            expires=expiration,
            details=details,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.principal_id == principal.id
        assert identity.password == password_hash
        assert identity.public_key == public_key
        assert identity.device_id == device_id
        assert identity.expires == expiration
        assert identity.details == details

    @pytest.mark.asyncio
    async def test_identity_query_by_principal(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test querying identities by principal ID."""
        identity1 = KPrincipalIdentity(
            principal_id=principal.id,
            device_id="device1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        identity2 = KPrincipalIdentity(
            principal_id=principal.id,
            device_id="device2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity1)
        session.add(identity2)
        await session.commit()

        # Query identities for this principal
        result_exec = await session.execute(
            select(KPrincipalIdentity).where(
                KPrincipalIdentity.principal_id == principal.id
            )
        )
        results = result_exec.scalars().all()

        assert len(results) == 2
        device_ids = {r.device_id for r in results}
        assert device_ids == {"device1", "device2"}

    @pytest.mark.asyncio
    async def test_identity_update(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test updating identity fields."""
        identity = KPrincipalIdentity(
            principal_id=principal.id,
            device_id="old-device",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        # Update fields
        new_password = "$2b$12$NEW_HASH"
        identity.password = new_password
        identity.device_id = "new-device"
        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.password == new_password
        assert identity.device_id == "new-device"

    @pytest.mark.asyncio
    async def test_identity_delete(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test deleting an identity."""
        identity = KPrincipalIdentity(
            principal_id=principal.id,
            device_id="to-delete",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        identity_id = identity.id

        # Delete the identity
        await session.delete(identity)
        await session.commit()

        # Verify it's deleted
        result = await session.get(KPrincipalIdentity, identity_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_identity_details_json_field(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test that details field correctly stores and retrieves JSON data."""
        details_data = {
            "auth_method": "oauth",
            "provider": "google",
            "mfa_enabled": True,
            "login_history": [
                {"timestamp": "2024-01-01T00:00:00Z", "ip": "192.168.1.1"},
                {"timestamp": "2024-01-02T00:00:00Z", "ip": "192.168.1.2"},
            ],
        }

        identity = KPrincipalIdentity(
            principal_id=principal.id,
            details=details_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.details == details_data
        assert identity.details["auth_method"] == "oauth"
        assert identity.details["provider"] == "google"
        assert identity.details["mfa_enabled"] is True
        assert len(identity.details["login_history"]) == 2

    @pytest.mark.asyncio
    async def test_identity_null_principal_id(self, session: AsyncSession, creator_id: UUID):
        """Test that identity can be created without a principal_id."""
        identity = KPrincipalIdentity(
            principal_id=None,
            device_id="standalone-device",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(identity)
        await session.commit()
        await session.refresh(identity)

        assert identity.principal_id is None
        assert identity.device_id == "standalone-device"

    @pytest.mark.asyncio
    async def test_multiple_identities_per_principal(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test that a principal can have multiple identities."""
        password_identity = KPrincipalIdentity(
            principal_id=principal.id,
            password="$2b$12$PASSWORD_HASH",
            details={"type": "password"},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        key_identity = KPrincipalIdentity(
            principal_id=principal.id,
            public_key=b"ssh-rsa KEY...",
            details={"type": "public_key"},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        device_identity = KPrincipalIdentity(
            principal_id=principal.id,
            device_id="mobile-123",
            details={"type": "device"},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(password_identity)
        session.add(key_identity)
        session.add(device_identity)
        await session.commit()

        # Query all identities for this principal
        result_exec = await session.execute(
            select(KPrincipalIdentity).where(
                KPrincipalIdentity.principal_id == principal.id
            )
        )
        identities = result_exec.scalars().all()

        assert len(identities) == 3
        types = {i.details["type"] for i in identities}
        assert types == {"password", "public_key", "device"}

    @pytest.mark.asyncio
    async def test_identity_expiration_check(self, session: AsyncSession, principal: KPrincipal, creator_id: UUID):
        """Test checking if an identity has expired."""
        past_date = datetime.now() - timedelta(days=1)
        future_date = datetime.now() + timedelta(days=1)

        expired_identity = KPrincipalIdentity(
            principal_id=principal.id,
            expires=past_date,
            device_id="expired",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        valid_identity = KPrincipalIdentity(
            principal_id=principal.id,
            expires=future_date,
            device_id="valid",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(expired_identity)
        session.add(valid_identity)
        await session.commit()

        # Query non-expired identities
        now = datetime.now()
        result_exec = await session.execute(
            select(KPrincipalIdentity).where(
                KPrincipalIdentity.principal_id == principal.id,
                KPrincipalIdentity.expires > now,
            )
        )
        valid_identities = result_exec.scalars().all()

        assert len(valid_identities) == 1
        assert valid_identities[0].device_id == "valid"
