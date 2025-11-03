"""Unit tests for authentication and security utilities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import bcrypt
import pytest
from jose import jwt

from app.core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models import KPrincipal, KPrincipalIdentity
from app.schemas.user import UserDetail


class TestPasswordHashing:
    """Test suite for password hashing functions."""

    def test_get_password_hash_returns_string(self):
        """Test that get_password_hash returns a string."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2

    def test_get_password_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "same_password"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Due to bcrypt salting, hashes should be different
        assert hash1 != hash2

    def test_get_password_hash_empty_password(self):
        """Test hashing an empty password."""
        password = ""
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_long_password(self):
        """Test hashing a very long password."""
        password = "a" * 1000
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_unicode_characters(self):
        """Test hashing password with unicode characters."""
        password = "пароль密码🔒"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0


class TestPasswordVerification:
    """Test suite for password verification."""

    @pytest.mark.asyncio
    async def test_verify_password_correct_password(self):
        """Test verifying a correct password."""
        password = "correct_password"
        hashed = get_password_hash(password)
        
        is_valid = await verify_password(password, hashed)
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_incorrect_password(self):
        """Test verifying an incorrect password."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(correct_password)
        
        is_valid = await verify_password(wrong_password, hashed)
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_password_empty_password(self):
        """Test verifying an empty password."""
        password = ""
        hashed = get_password_hash(password)
        
        is_valid = await verify_password(password, hashed)
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "Password123"
        hashed = get_password_hash(password)
        
        # Test with different case
        is_valid = await verify_password("password123", hashed)
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_password_special_characters(self):
        """Test verifying password with special characters."""
        password = "p@ssw0rd!#$%"
        hashed = get_password_hash(password)
        
        is_valid = await verify_password(password, hashed)
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_unicode_characters(self):
        """Test verifying password with unicode characters."""
        password = "пароль密码🔒"
        hashed = get_password_hash(password)
        
        is_valid = await verify_password(password, hashed)
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_long_password(self):
        """Test verifying a long password."""
        password = "a" * 500
        hashed = get_password_hash(password)
        
        is_valid = await verify_password(password, hashed)
        
        assert is_valid is True


class TestAccessTokenCreation:
    """Test suite for access token creation."""

    @pytest.mark.asyncio
    async def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a string."""
        data = {"sub": "user123", "scope": "test"}
        token = await create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_create_access_token_contains_data(self):
        """Test that created token contains the provided data."""
        user_id = str(uuid4())
        data = {"sub": user_id, "scope": "test-scope"}
        
        token = await create_access_token(data)
        
        # Decode token without verification to check contents
        from app.core.auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["sub"] == user_id
        assert decoded["scope"] == "test-scope"
        assert "exp" in decoded

    @pytest.mark.asyncio
    async def test_create_access_token_with_custom_expiry(self):
        """Test creating access token with custom expiration time."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        
        current_time_before = datetime.now(UTC).replace(tzinfo=None)
        token = await create_access_token(data, expires_delta)
        
        from app.core.auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check that expiration is set
        assert "exp" in decoded
        # Use utcfromtimestamp to get naive UTC datetime (matching the token creation)
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        
        # Expiration should be roughly 30 minutes from when token was created
        time_diff = exp_time - current_time_before
        assert 29 <= time_diff.total_seconds() / 60 <= 31  # Allow 1 minute margin

    @pytest.mark.asyncio
    async def test_create_access_token_default_expiry(self):
        """Test that default expiration is applied when not specified."""
        data = {"sub": "user123"}
        
        current_time_before = datetime.now(UTC).replace(tzinfo=None)
        token = await create_access_token(data)
        
        from app.core.auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "exp" in decoded
        # Use utcfromtimestamp to get naive UTC datetime (matching the token creation)
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        
        # Should be in the future (at least a few minutes)
        time_diff = exp_time - current_time_before
        assert time_diff.total_seconds() > 0

    @pytest.mark.asyncio
    async def test_create_access_token_does_not_modify_input(self):
        """Test that creating token doesn't modify input data dict."""
        data = {"sub": "user123", "scope": "test"}
        original_data = data.copy()
        
        await create_access_token(data)
        
        # Original data should not be modified
        assert data == original_data

    @pytest.mark.asyncio
    async def test_create_access_token_different_data_different_tokens(self):
        """Test that different data produces different tokens."""
        data1 = {"sub": "user1"}
        data2 = {"sub": "user2"}
        
        token1 = await create_access_token(data1)
        token2 = await create_access_token(data2)
        
        assert token1 != token2


class TestRefreshTokenCreation:
    """Test suite for refresh token creation."""

    @pytest.mark.asyncio
    async def test_create_refresh_token_returns_string(self):
        """Test that create_refresh_token returns a string."""
        data = {"sub": "user123"}
        token = await create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_create_refresh_token_contains_data(self):
        """Test that created refresh token contains the provided data."""
        user_id = str(uuid4())
        data = {"sub": user_id, "scope": "test-scope"}
        
        token = await create_refresh_token(data)
        
        from app.core.auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["sub"] == user_id
        assert decoded["scope"] == "test-scope"
        assert "exp" in decoded

    @pytest.mark.asyncio
    async def test_create_refresh_token_with_custom_expiry(self):
        """Test creating refresh token with custom expiration time."""
        data = {"sub": "user123"}
        expires_delta = timedelta(days=7)
        
        current_time_before = datetime.now(UTC).replace(tzinfo=None)
        token = await create_refresh_token(data, expires_delta)
        
        from app.core.auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "exp" in decoded
        # Use utcfromtimestamp to get naive UTC datetime (matching the token creation)
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        
        # Expiration should be roughly 7 days from when token was created
        time_diff = exp_time - current_time_before
        assert 6.9 <= time_diff.total_seconds() / 86400 <= 7.1  # Allow margin

    @pytest.mark.asyncio
    async def test_create_refresh_token_default_expiry(self):
        """Test that default expiration is applied for refresh token."""
        data = {"sub": "user123"}
        
        token = await create_refresh_token(data)
        
        from app.core.auth import ALGORITHM, SECRET_KEY
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"])
        current_time = datetime.now(UTC).replace(tzinfo=None)
        
        # Should be in the future
        assert exp_time > current_time

    @pytest.mark.asyncio
    async def test_create_refresh_token_longer_than_access_token(self):
        """Test that refresh token expiry is longer than access token."""
        data = {"sub": "user123"}
        
        access_token = await create_access_token(data)
        refresh_token = await create_refresh_token(data)
        
        from app.core.auth import ALGORITHM, SECRET_KEY
        access_decoded = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_decoded = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Refresh token should expire later than access token
        assert refresh_decoded["exp"] > access_decoded["exp"]


class TestTokenVerification:
    """Test suite for token verification."""

    @pytest.mark.asyncio
    async def test_verify_token_valid_token(self):
        """Test verifying a valid token."""
        data = {"sub": "user123", "scope": "test"}
        token = await create_access_token(data)
        
        payload = await verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["scope"] == "test"

    @pytest.mark.asyncio
    async def test_verify_token_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = await verify_token(invalid_token)
        
        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_expired_token(self):
        """Test verifying an expired token."""
        data = {"sub": "user123"}
        # Create token with negative expiry (already expired)
        expires_delta = timedelta(seconds=-1)
        token = await create_access_token(data, expires_delta)
        
        payload = await verify_token(token)
        
        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_missing_sub(self):
        """Test verifying token without 'sub' claim."""
        # Create token manually without 'sub'
        from app.core.auth import ALGORITHM, SECRET_KEY
        data = {"scope": "test", "exp": datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=15)}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        payload = await verify_token(token)
        
        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_empty_string(self):
        """Test verifying empty token string."""
        payload = await verify_token("")
        
        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_malformed_token(self):
        """Test verifying malformed token."""
        malformed_tokens = [
            "not.a.token",
            "only_one_part",
            "two.parts",
            ".....",
            "Bearer token",
        ]
        
        for token in malformed_tokens:
            payload = await verify_token(token)
            assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_preserves_all_claims(self):
        """Test that token verification preserves all claims."""
        data = {
            "sub": "user123",
            "scope": "test-scope",
            "role": "admin",
            "custom_claim": "custom_value"
        }
        token = await create_access_token(data)
        
        payload = await verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["scope"] == "test-scope"
        assert payload["role"] == "admin"
        assert payload["custom_claim"] == "custom_value"


class TestTokenIntegration:
    """Integration tests for token creation and verification."""

    @pytest.mark.asyncio
    async def test_access_token_full_lifecycle(self):
        """Test creating and verifying an access token."""
        user_id = str(uuid4())
        data = {"sub": user_id, "scope": "global"}
        
        # Create token
        token = await create_access_token(data)
        assert isinstance(token, str)
        
        # Verify token
        payload = await verify_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["scope"] == "global"

    @pytest.mark.asyncio
    async def test_refresh_token_full_lifecycle(self):
        """Test creating and verifying a refresh token."""
        user_id = str(uuid4())
        data = {"sub": user_id, "scope": "global"}
        
        # Create refresh token
        token = await create_refresh_token(data)
        assert isinstance(token, str)
        
        # Verify token
        payload = await verify_token(token)
        assert payload is not None
        assert payload["sub"] == user_id

    @pytest.mark.asyncio
    async def test_multiple_tokens_independent(self):
        """Test that multiple tokens are independent."""
        data1 = {"sub": "user1", "scope": "scope1"}
        data2 = {"sub": "user2", "scope": "scope2"}
        
        token1 = await create_access_token(data1)
        token2 = await create_access_token(data2)
        
        payload1 = await verify_token(token1)
        payload2 = await verify_token(token2)
        
        assert payload1["sub"] == "user1"
        assert payload2["sub"] == "user2"
        assert payload1["scope"] == "scope1"
        assert payload2["scope"] == "scope2"

    @pytest.mark.asyncio
    async def test_password_and_token_workflow(self):
        """Test complete password hashing and token creation workflow."""
        # Hash password
        password = "secure_password_123"
        hashed = get_password_hash(password)
        
        # Verify password
        is_valid = await verify_password(password, hashed)
        assert is_valid is True
        
        # Create token after successful verification
        user_id = str(uuid4())
        token_data = {"sub": user_id, "scope": "global"}
        token = await create_access_token(token_data)
        
        # Verify token
        payload = await verify_token(token)
        assert payload is not None
        assert payload["sub"] == user_id


class TestAuthenticateUser:
    """Test suite for authenticate_user function with database integration."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, async_session, creator_id):
        """Test successful user authentication with valid credentials."""
        # Create a principal
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="testuser",
            primary_email="test@example.com",
            human=True,
            enabled=True,
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        await async_session.refresh(principal)
        
        # Create identity with password
        password = "test_password_123"
        hashed_password = get_password_hash(password)
        identity = KPrincipalIdentity(
            principal_id=user_id,
            password=hashed_password,
            created_by=user_id,
            last_modified_by=user_id,
        )
        async_session.add(identity)
        await async_session.commit()
        
        # Authenticate
        result = await authenticate_user("testuser", password, async_session)
        
        # Verify
        assert result is not None
        assert isinstance(result, UserDetail)
        assert result.username == "testuser"
        assert result.id == user_id

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, async_session, creator_id):
        """Test authentication fails with wrong password."""
        # Create principal and identity
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="testuser2",
            primary_email="test2@example.com",
            human=True,
            enabled=True,
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        await async_session.refresh(principal)
        
        password = "correct_password"
        hashed_password = get_password_hash(password)
        identity = KPrincipalIdentity(
            principal_id=user_id,
            password=hashed_password,
            created_by=user_id,
            last_modified_by=user_id,
        )
        async_session.add(identity)
        await async_session.commit()
        
        # Try wrong password
        result = await authenticate_user("testuser2", "wrong_password", async_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, async_session):
        """Test authentication fails when user doesn't exist."""
        result = await authenticate_user("nonexistent", "password", async_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_no_password_identity(self, async_session, creator_id):
        """Test authentication fails when user has no password identity."""
        # Create principal without identity
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="nopassword",
            primary_email="nopass@example.com",
            human=True,
            enabled=True,
            first_name="No",
            last_name="Password",
            display_name="No Password",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        
        # No identity added
        result = await authenticate_user("nopassword", "anypassword", async_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_null_password(self, async_session, creator_id):
        """Test authentication fails when password field is None."""
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="nullpass",
            primary_email="null@example.com",
            human=True,
            enabled=True,
            first_name="Null",
            last_name="Pass",
            display_name="Null Pass",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        await async_session.refresh(principal)
        
        # Create identity with null password
        identity = KPrincipalIdentity(
            principal_id=user_id,
            password=None,
            created_by=user_id,
            last_modified_by=user_id,
        )
        async_session.add(identity)
        await async_session.commit()
        
        result = await authenticate_user("nullpass", "anypassword", async_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_disabled_account(self, async_session, creator_id):
        """Test authentication fails for disabled accounts."""
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="disabled",
            primary_email="disabled@example.com",
            human=True,
            enabled=False,  # Disabled
            first_name="Disabled",
            last_name="User",
            display_name="Disabled User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        
        password = "password123"
        hashed_password = get_password_hash(password)
        identity = KPrincipalIdentity(
            principal_id=user_id,
            password=hashed_password,
            created_by=user_id,
            last_modified_by=user_id,
        )
        async_session.add(identity)
        await async_session.commit()
        
        result = await authenticate_user("disabled", password, async_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_non_human_principal(self, async_session, creator_id):
        """Test authentication fails for non-human principals (service accounts)."""
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="global",
            username="serviceaccount",
            primary_email="service@example.com",
            human=False,  # Not human
            enabled=True,
            first_name="Service",
            last_name="Account",
            display_name="Service Account",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        
        password = "password123"
        hashed_password = get_password_hash(password)
        identity = KPrincipalIdentity(
            principal_id=user_id,
            password=hashed_password,
            created_by=user_id,
            last_modified_by=user_id,
        )
        async_session.add(identity)
        await async_session.commit()
        
        result = await authenticate_user("serviceaccount", password, async_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_scope(self, async_session, creator_id):
        """Test authentication fails for users not in 'global' scope."""
        user_id = uuid4()
        principal = KPrincipal(
            id=user_id,
            scope="custom-scope",  # Not global
            username="customscope",
            primary_email="custom@example.com",
            human=True,
            enabled=True,
            first_name="Custom",
            last_name="Scope",
            display_name="Custom Scope",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        async_session.add(principal)
        await async_session.commit()
        
        password = "password123"
        hashed_password = get_password_hash(password)
        identity = KPrincipalIdentity(
            principal_id=user_id,
            password=hashed_password,
            created_by=user_id,
            last_modified_by=user_id,
        )
        async_session.add(identity)
        await async_session.commit()
        
        result = await authenticate_user("customscope", password, async_session)
        
        assert result is None

