from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .user import Token


# Registration schemas
class Fido2RegistrationBeginRequest(BaseModel):
    """Request to begin FIDO2 credential registration."""

    username: str | None = Field(
        default=None,
        description="Username for registration (optional if user is already authenticated)",
    )


class Fido2RegistrationBeginResponse(BaseModel):
    """Response containing credential creation options for the browser/client."""

    publicKey: dict[str, Any] = Field(
        description="PublicKeyCredentialCreationOptions for navigator.credentials.create()"
    )


class Fido2RegistrationCompleteRequest(BaseModel):
    """Request to complete FIDO2 credential registration."""

    credential: dict[str, Any] = Field(
        description="Attestation response from navigator.credentials.create()"
    )
    nickname: str | None = Field(
        default=None, description="User-friendly name for this credential"
    )
    session_id: str = Field(description="Session ID from registration begin")


class Fido2RegistrationCompleteResponse(BaseModel):
    """Response after successful registration."""

    credential_id: str = Field(description="Base64-encoded credential ID")
    message: str = Field(default="FIDO2 credential registered successfully")


# Authentication schemas
class Fido2AuthenticationBeginRequest(BaseModel):
    """Request to begin FIDO2 authentication."""

    username: str | None = Field(
        default=None,
        description="Username (optional for passwordless/discoverable credentials)",
    )
    require_user_verification: bool = Field(
        default=False,
        description="Require user verification (PIN, biometric, etc.)",
    )


class Fido2AuthenticationBeginResponse(BaseModel):
    """Response containing credential request options for the browser/client."""

    publicKey: dict[str, Any] = Field(
        description="PublicKeyCredentialRequestOptions for navigator.credentials.get()"
    )


class Fido2AuthenticationCompleteRequest(BaseModel):
    """Request to complete FIDO2 authentication."""

    credential: dict[str, Any] = Field(
        description="Assertion response from navigator.credentials.get()"
    )
    session_id: str = Field(description="Session ID from authentication begin")


class Fido2AuthenticationCompleteResponse(BaseModel):
    """Response after successful authentication (for passwordless flow)."""

    token: Token = Field(description="JWT access and refresh tokens")


class Fido2VerificationToken(BaseModel):
    """Temporary token issued after FIDO2 verification for 2FA completion."""

    verification_token: str = Field(
        description="Temporary token to complete 2FA login flow"
    )
    expires_in: int = Field(default=300, description="Token expiration time in seconds")


# 2FA Login schemas
class Fido2TwoFactorLoginRequest(BaseModel):
    """Request for combined password + FIDO2 two-factor authentication."""

    username: str
    password: str
    credential: dict[str, Any] | None = Field(
        default=None,
        description="FIDO2 assertion (if None, will return challenge for FIDO2 step)",
    )


class Fido2TwoFactorLoginResponse(BaseModel):
    """Response for 2FA login - either challenge or token."""

    token: Token | None = Field(
        default=None, description="Tokens if authentication is complete"
    )
    publicKey: dict[str, Any] | None = Field(
        default=None, description="Challenge if FIDO2 verification is needed"
    )
    message: str | None = Field(default=None)


# Credential management schemas
class Fido2CredentialDetail(BaseModel):
    """Detailed information about a FIDO2 credential."""

    id: UUID
    credential_id: str = Field(description="Base64-encoded credential ID")
    nickname: str | None = None
    aaguid: str = Field(description="Hex-encoded authenticator model identifier")
    transports: list[str]
    is_discoverable: bool
    last_used: datetime | None = None
    created: datetime


class Fido2CredentialList(BaseModel):
    """List of FIDO2 credentials."""

    credentials: list[Fido2CredentialDetail]
    total: int


class Fido2CredentialUpdateRequest(BaseModel):
    """Request to update a FIDO2 credential."""

    nickname: str = Field(max_length=255, description="New nickname for the credential")


class Fido2CredentialDeleteResponse(BaseModel):
    """Response after deleting a credential."""

    message: str = Field(default="FIDO2 credential deleted successfully")


__all__ = [
    "Fido2RegistrationBeginRequest",
    "Fido2RegistrationBeginResponse",
    "Fido2RegistrationCompleteRequest",
    "Fido2RegistrationCompleteResponse",
    "Fido2AuthenticationBeginRequest",
    "Fido2AuthenticationBeginResponse",
    "Fido2AuthenticationCompleteRequest",
    "Fido2AuthenticationCompleteResponse",
    "Fido2VerificationToken",
    "Fido2TwoFactorLoginRequest",
    "Fido2TwoFactorLoginResponse",
    "Fido2CredentialDetail",
    "Fido2CredentialList",
    "Fido2CredentialUpdateRequest",
    "Fido2CredentialDeleteResponse",
]
