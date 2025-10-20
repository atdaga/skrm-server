from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_principal import KPrincipal
    from .k_team import KTeam


class KTeamMember(SQLModel, table=True):
    __tablename__ = "k_team_member"

    team_id: UUID = Field(
        sa_column=Column(ForeignKey("k_team.id", ondelete="CASCADE"), primary_key=True)
    )
    principal_id: UUID = Field(foreign_key="k_principal.id", primary_key=True)
    scope: str = Field(..., max_length=255)
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    team: "KTeam" = Relationship(back_populates="team_members")
    principal: "KPrincipal" = Relationship(back_populates="team_memberships")


__all__ = ["KTeamMember"]
