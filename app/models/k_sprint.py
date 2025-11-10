from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import JSON, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_organization import KOrganization
    from .k_sprint_task import KSprintTask
    from .k_sprint_team import KSprintTeam


class SprintStatus(str, Enum):
    """Sprint status enumeration."""

    BACKLOG = "Backlog"
    ACTIVE = "Active"
    DONE = "Done"


class KSprint(SQLModel, table=True):
    __tablename__ = "k_sprint"

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    title: str | None = Field(default=None, sa_type=Text)
    status: SprintStatus = Field(default=SprintStatus.BACKLOG)
    end_ts: datetime | None = Field(default=None)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship()
    sprint_teams: list["KSprintTeam"] = Relationship(
        back_populates="sprint", sa_relationship_kwargs={"passive_deletes": True}
    )
    sprint_tasks: list["KSprintTask"] = Relationship(
        back_populates="sprint", sa_relationship_kwargs={"passive_deletes": True}
    )


__all__ = ["KSprint", "SprintStatus"]
