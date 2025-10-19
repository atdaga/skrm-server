from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship


class KTeam(SQLModel, table=True):
    __tablename__ = "k_team"
    __table_args__ = (
        UniqueConstraint('scope', 'name'),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scope: str = Field(default="global", max_length=255)
    name: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    team_members: list["KTeamMember"] = Relationship(back_populates="team", cascade_delete=True)


__all__ = ["KTeam"]
