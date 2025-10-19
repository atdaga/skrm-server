from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field


class KPrincipalIdentity(SQLModel, table=True):
    __tablename__ = "k_principal_identity"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    principal_id: UUID | None = Field(default=None, foreign_key="k_principal.id", index=True)
    password: str | None = Field(default=None, max_length=255)  # bcrypt hash of user's password
    public_key: bytes | None = None
    device_id: str | None = Field(default=None, max_length=255)
    expires: datetime | None = None
    details: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KPrincipalIdentity"]
