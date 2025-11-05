"""Unit tests for FIDO2 core server functionality."""

import base64
import secrets
from datetime import datetime, timedelta

from app.core.fido2_server import (
    aaguid_to_hex,
    credential_id_from_base64,
    credential_id_to_base64,
    credential_to_descriptor,
    encode_options_for_client,
    generate_session_id,
    get_fido2_server,
    retrieve_challenge,
    store_challenge,
)


class TestFido2ServerInstance:
    """Test suite for get_fido2_server function."""

    def test_get_fido2_server_returns_instance(self):
        """Test that get_fido2_server returns a Fido2Server instance."""
        from fido2.server import Fido2Server

        server = get_fido2_server()
        assert isinstance(server, Fido2Server)
        assert server.rp.id == "localhost"  # Default from config
        assert server.rp.name == "Python Server"  # Default from config

    def test_get_fido2_server_returns_same_config(self):
        """Test that multiple calls return consistent configuration."""
        server1 = get_fido2_server()
        server2 = get_fido2_server()

        assert server1.rp.id == server2.rp.id
        assert server1.rp.name == server2.rp.name


class TestChallengeStorage:
    """Test suite for challenge storage and retrieval."""

    def test_store_and_retrieve_challenge(self):
        """Test storing and retrieving a challenge."""
        session_id = "test_session_123"
        challenge = secrets.token_bytes(32)

        store_challenge(session_id, challenge)
        retrieved = retrieve_challenge(session_id)

        assert retrieved == challenge

    def test_retrieve_removes_challenge(self):
        """Test that retrieving a challenge removes it from storage."""
        session_id = "test_session_456"
        challenge = secrets.token_bytes(32)

        store_challenge(session_id, challenge)
        retrieve_challenge(session_id)  # First retrieval
        second_retrieval = retrieve_challenge(session_id)  # Second retrieval

        assert second_retrieval is None

    def test_retrieve_nonexistent_challenge(self):
        """Test retrieving a challenge that doesn't exist."""
        result = retrieve_challenge("nonexistent_session")
        assert result is None

    def test_retrieve_expired_challenge(self):
        """Test that expired challenges are not retrieved."""
        from app.core import fido2_server as fs

        session_id = "expired_session"
        challenge = secrets.token_bytes(32)

        # Store with expired timestamp
        expired_time = datetime.now() - timedelta(minutes=10)
        fs._challenge_store[session_id] = (challenge, expired_time)

        result = retrieve_challenge(session_id)
        assert result is None


class TestSessionIdGeneration:
    """Test suite for session ID generation."""

    def test_generate_session_id_returns_string(self):
        """Test that generate_session_id returns a string."""
        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_generate_session_id_unique(self):
        """Test that generated session IDs are unique."""
        session_ids = {generate_session_id() for _ in range(100)}
        assert len(session_ids) == 100  # All should be unique


class TestCredentialIdConversion:
    """Test suite for credential ID encoding/decoding."""

    def test_credential_id_to_base64(self):
        """Test converting credential ID bytes to base64."""
        credential_id = b"test_credential_id_12345"
        result = credential_id_to_base64(credential_id)

        assert isinstance(result, str)
        # Should not have padding (stripped)
        assert "=" not in result or result.endswith("=")

    def test_credential_id_from_base64(self):
        """Test converting base64 string to credential ID bytes."""
        credential_id = b"test_credential_id_12345"
        encoded = credential_id_to_base64(credential_id)
        decoded = credential_id_from_base64(encoded)

        assert decoded == credential_id

    def test_credential_id_roundtrip(self):
        """Test round-trip encoding and decoding."""
        original = secrets.token_bytes(32)
        encoded = credential_id_to_base64(original)
        decoded = credential_id_from_base64(encoded)

        assert decoded == original

    def test_credential_id_from_base64_with_padding(self):
        """Test decoding base64 with padding."""
        # Create a string that needs padding
        credential_id = b"test"
        encoded = base64.urlsafe_b64encode(credential_id).decode("utf-8")
        # Remove padding
        encoded = encoded.rstrip("=")

        decoded = credential_id_from_base64(encoded)
        assert decoded == credential_id


class TestAaguidConversion:
    """Test suite for AAGUID hex encoding."""

    def test_aaguid_to_hex(self):
        """Test converting AAGUID bytes to hex string."""
        aaguid = bytes.fromhex("00112233445566778899aabbccddeeff")
        result = aaguid_to_hex(aaguid)

        assert result == "00112233445566778899aabbccddeeff"
        assert isinstance(result, str)

    def test_aaguid_to_hex_empty(self):
        """Test converting empty AAGUID."""
        aaguid = b""
        result = aaguid_to_hex(aaguid)
        assert result == ""


class TestCredentialToDescriptor:
    """Test suite for credential descriptor creation."""

    def test_credential_to_descriptor_basic(self):
        """Test creating a basic credential descriptor."""
        from fido2.webauthn import PublicKeyCredentialDescriptor

        credential_id = secrets.token_bytes(32)
        descriptor = credential_to_descriptor(credential_id)

        assert isinstance(descriptor, PublicKeyCredentialDescriptor)
        assert descriptor.type == "public-key"
        assert descriptor.id == credential_id
        assert descriptor.transports == []

    def test_credential_to_descriptor_with_transports(self):
        """Test creating a credential descriptor with transports."""
        from fido2.webauthn import PublicKeyCredentialDescriptor

        credential_id = secrets.token_bytes(32)
        transports = ["usb", "nfc"]
        descriptor = credential_to_descriptor(credential_id, transports)

        assert isinstance(descriptor, PublicKeyCredentialDescriptor)
        assert descriptor.transports == transports


class TestEncodeOptionsForClient:
    """Test suite for encoding options for client."""

    def test_encode_simple_dict(self):
        """Test encoding a simple dictionary."""
        options = {
            "key1": "value1",
            "key2": 123,
            "key3": True,
        }
        result = encode_options_for_client(options)

        assert result == options

    def test_encode_bytes_to_base64(self):
        """Test encoding bytes values to base64."""
        challenge = secrets.token_bytes(32)
        options = {"challenge": challenge, "other": "value"}

        result = encode_options_for_client(options)

        assert isinstance(result["challenge"], str)
        assert result["other"] == "value"
        # Verify it's valid base64
        decoded = base64.urlsafe_b64decode(result["challenge"] + "===")
        assert decoded == challenge

    def test_encode_nested_dict(self):
        """Test encoding nested dictionaries."""
        challenge = secrets.token_bytes(32)
        options = {
            "level1": {
                "level2": {
                    "challenge": challenge,
                    "text": "value",
                },
                "number": 42,
            }
        }

        result = encode_options_for_client(options)

        assert isinstance(result["level1"]["level2"]["challenge"], str)
        assert result["level1"]["level2"]["text"] == "value"
        assert result["level1"]["number"] == 42

    def test_encode_list_with_dicts(self):
        """Test encoding lists containing dictionaries."""
        credential_id = secrets.token_bytes(32)
        options = {
            "credentials": [
                {"id": credential_id, "type": "public-key"},
                {"id": credential_id, "type": "public-key"},
            ]
        }

        result = encode_options_for_client(options)

        assert len(result["credentials"]) == 2
        assert isinstance(result["credentials"][0]["id"], str)
        assert result["credentials"][0]["type"] == "public-key"

    def test_encode_empty_dict(self):
        """Test encoding an empty dictionary."""
        result = encode_options_for_client({})
        assert result == {}

    def test_encode_preserves_none(self):
        """Test that None values are preserved."""
        options = {"key": None}
        result = encode_options_for_client(options)
        assert result["key"] is None
