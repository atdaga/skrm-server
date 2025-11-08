from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import JSON, LargeBinary
from sqlmodel import Field, SQLModel


class KFido2Credential(SQLModel, table=True):
    __tablename__ = "k_fido2_credential"

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    principal_id: UUID = Field(foreign_key="k_principal.id", index=True)
    credential_id: bytes = Field(
        sa_type=LargeBinary, unique=True, index=True
    )  # Credential ID from authenticator
    public_key: bytes = Field(
        sa_type=LargeBinary
    )  # COSE-encoded public key from authenticator
    sign_count: int = Field(default=0)  # Signature counter for cloned device detection
    aaguid: bytes = Field(sa_type=LargeBinary)  # Authenticator model identifier
    transports: list[str] = Field(
        default_factory=list, sa_type=JSON
    )  # Supported transports (usb, nfc, ble, internal)
    is_discoverable: bool = Field(
        default=False
    )  # Whether it's a resident key (discoverable credential)
    nickname: str | None = Field(
        default=None, max_length=255
    )  # User-friendly name (e.g., "YubiKey 5", "iPhone TouchID")
    last_used: datetime | None = None  # Track usage for security monitoring
    deleted: bool = Field(default=False)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KFido2Credential"]
