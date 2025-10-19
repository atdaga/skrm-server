from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import SQLModel, Field


class KPrincipal(SQLModel, table=True):
    __tablename__ = "k_principal"
    __table_args__ = (
        UniqueConstraint('scope', 'username'),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scope: str = Field(default="global", max_length=255)
    username: str = Field(..., max_length=255)
    primary_email: str = Field(..., max_length=255)
    primary_email_verified: bool = Field(default=False)
    primary_phone: str | None = Field(default=None, max_length=255)
    primary_phone_verified: bool = Field(default=False)
    human: bool = Field(default=True)
    enabled: bool = Field(default=True)
    time_zone: str = Field(default="UTC", max_length=255)
    name_prefix: str | None = Field(default=None, max_length=255)
    first_name: str = Field(..., max_length=255)
    middle_name: str | None = Field(default=None, max_length=255)
    last_name: str = Field(..., max_length=255)
    name_suffix: str | None = Field(default=None, max_length=255)
    display_name: str = Field(..., max_length=255)
    default_locale: str = Field(default='en', max_length=255)
    system_role: str = Field(default="system_user")
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KPrincipal"]
