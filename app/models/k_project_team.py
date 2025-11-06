from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_project import KProject
    from .k_team import KTeam


class KProjectTeam(SQLModel, table=True):
    __tablename__ = "k_project_team"

    project_id: UUID = Field(foreign_key="k_project.id", primary_key=True)
    team_id: UUID = Field(
        sa_column=Column(ForeignKey("k_team.id", ondelete="CASCADE"), primary_key=True)
    )
    org_id: UUID
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    project: "KProject" = Relationship(back_populates="project_teams")
    team: "KTeam" = Relationship(back_populates="project_teams")


__all__ = ["KProjectTeam"]
