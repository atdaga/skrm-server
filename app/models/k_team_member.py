from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field


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


__all__ = ["KTeamMember"]
