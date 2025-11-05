"""Core FIDO2/WebAuthn server functionality."""

import base64
import secrets
from datetime import datetime, timedelta
from typing import Any

from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestationObject,
    AuthenticatorData,
    CollectedClientData,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
)

from ..config import settings

# In-memory challenge storage (use Redis in production)
_challenge_store: dict[str, tuple[bytes, datetime]] = {}


def get_fido2_server() -> Fido2Server:
    """Get configured FIDO2Server instance.

    Returns:
        Fido2Server instance configured with RP settings
    """
    rp = PublicKeyCredentialRpEntity(name=settings.rp_name, id=settings.rp_id)
    return Fido2Server(rp, attestation="none")


def store_challenge(session_id: str, challenge: bytes) -> None:
    """Store a challenge temporarily.

    Args:
        session_id: Unique session identifier
        challenge: Challenge bytes to store
    """
    expiration = datetime.now() + timedelta(minutes=5)
    _challenge_store[session_id] = (challenge, expiration)


def retrieve_challenge(session_id: str) -> bytes | None:
    """Retrieve and remove a stored challenge.

    Args:
        session_id: Unique session identifier

    Returns:
        Challenge bytes if found and not expired, None otherwise
    """
    # Clean up expired challenges
    now = datetime.now()
    expired_keys = [k for k, (_, exp) in _challenge_store.items() if exp < now]
    for key in expired_keys:
        del _challenge_store[key]

    # Retrieve and remove challenge
    if session_id in _challenge_store:
        challenge, expiration = _challenge_store.pop(session_id)
        if expiration > now:
            return challenge
    return None


def generate_session_id() -> str:
    """Generate a unique session ID for challenge storage.

    Returns:
        Random session ID string
    """
    return secrets.token_urlsafe(32)


def credential_id_to_base64(credential_id: bytes) -> str:
    """Convert credential ID bytes to base64 string for JSON transport.

    Args:
        credential_id: Credential ID bytes

    Returns:
        Base64-encoded credential ID
    """
    return base64.urlsafe_b64encode(credential_id).decode("utf-8").rstrip("=")


def credential_id_from_base64(credential_id_b64: str) -> bytes:
    """Convert base64 credential ID string to bytes.

    Args:
        credential_id_b64: Base64-encoded credential ID

    Returns:
        Credential ID bytes
    """
    # Add padding if needed
    padding = 4 - (len(credential_id_b64) % 4)
    if padding != 4:
        credential_id_b64 += "=" * padding
    return base64.urlsafe_b64decode(credential_id_b64)


def aaguid_to_hex(aaguid: bytes) -> str:
    """Convert AAGUID bytes to hex string.

    Args:
        aaguid: AAGUID bytes

    Returns:
        Hex-encoded AAGUID
    """
    return aaguid.hex()


def create_user_entity(
    user_id: str, username: str, display_name: str
) -> PublicKeyCredentialUserEntity:  # pragma: no cover
    """Create a PublicKeyCredentialUserEntity for registration.

    Args:
        user_id: User ID (UUID as string)
        username: Username
        display_name: User's display name

    Returns:
        PublicKeyCredentialUserEntity for registration options
    """
    return PublicKeyCredentialUserEntity(
        id=user_id.encode("utf-8"), name=username, display_name=display_name
    )


def parse_client_data(client_data_json: str) -> CollectedClientData:  # pragma: no cover
    """Parse client data JSON.

    Args:
        client_data_json: Base64-encoded client data JSON

    Returns:
        CollectedClientData object
    """
    return CollectedClientData(base64.urlsafe_b64decode(client_data_json))


def parse_attestation_object(
    attestation_object: str,
) -> AttestationObject:  # pragma: no cover
    """Parse attestation object.

    Args:
        attestation_object: Base64-encoded attestation object

    Returns:
        AttestationObject
    """
    return AttestationObject(base64.urlsafe_b64decode(attestation_object))


def parse_authenticator_data(
    authenticator_data: str,
) -> AuthenticatorData:  # pragma: no cover
    """Parse authenticator data.

    Args:
        authenticator_data: Base64-encoded authenticator data

    Returns:
        AuthenticatorData object
    """
    return AuthenticatorData(base64.urlsafe_b64decode(authenticator_data))


def credential_to_descriptor(
    credential_id: bytes, transports: list[str] | None = None
) -> PublicKeyCredentialDescriptor:
    """Create a PublicKeyCredentialDescriptor from credential data.

    Args:
        credential_id: Credential ID bytes
        transports: List of supported transports

    Returns:
        PublicKeyCredentialDescriptor for authentication options
    """
    return PublicKeyCredentialDescriptor(
        type="public-key", id=credential_id, transports=transports or []
    )


def encode_options_for_client(options: dict[str, Any]) -> dict[str, Any]:
    """Encode server options for client (browser).

    Converts bytes to base64 strings for JSON transport.

    Args:
        options: Options dict from Fido2Server

    Returns:
        JSON-serializable options dict
    """
    result: dict[str, Any] = {}

    for key, value in options.items():
        if isinstance(value, bytes):
            result[key] = base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")
        elif isinstance(value, dict):
            result[key] = encode_options_for_client(value)
        elif isinstance(value, list):
            result[key] = [
                encode_options_for_client(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


__all__ = [
    "get_fido2_server",
    "store_challenge",
    "retrieve_challenge",
    "generate_session_id",
    "credential_id_to_base64",
    "credential_id_from_base64",
    "aaguid_to_hex",
    "create_user_entity",
    "parse_client_data",
    "parse_attestation_object",
    "parse_authenticator_data",
    "credential_to_descriptor",
    "encode_options_for_client",
]
