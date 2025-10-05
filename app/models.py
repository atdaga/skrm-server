from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class KUser(SQLModel, table=True):
    __tablename__ = "k_user"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    alias: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


class KPrincipalIdentity(SQLModel, table=True):
    __tablename__ = "k_principal_identity"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    password: str | None = Field(default=None, max_length=255)
    public_key: bytes | None = None
    device_id: str | None = Field(default=None, max_length=255)
    expires: datetime | None = None
    details: dict = Field(default_factory=dict)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


class KTeam(SQLModel, table=True):
    __tablename__ = "k_team"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


class KTeamMember(SQLModel, table=True):
    __tablename__ = "k_team_member"

    team_id: UUID = Field(foreign_key="k_team.id", primary_key=True)
    user_id: UUID = Field(foreign_key="k_user.id", primary_key=True)
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KUser", "KPrincipalIdentity", "KTeam", "KTeamMember"]