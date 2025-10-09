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


class KTeam(SQLModel, table=True):
    __tablename__ = "k_team"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


class KTeamMember(SQLModel, table=True):
    __tablename__ = "k_team_member"

    team_id: UUID = Field(foreign_key="k_team.id", primary_key=True)
    principal_id: UUID = Field(foreign_key="k_principal.id", primary_key=True)
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KPrincipal", "KPrincipalIdentity", "KTeam", "KTeamMember"]