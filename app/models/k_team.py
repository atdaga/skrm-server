from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.repr_mixin import SecureReprMixin

if TYPE_CHECKING:
    from .k_organization import KOrganization
    from .k_project_team import KProjectTeam
    from .k_sprint_team import KSprintTeam
    from .k_team_member import KTeamMember
    from .k_team_reviewer import KTeamReviewer


class KTeam(SecureReprMixin, SQLModel, table=True):
    __tablename__ = "k_team"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    name: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship()
    team_members: list["KTeamMember"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    team_reviewers: list["KTeamReviewer"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    project_teams: list["KProjectTeam"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    sprint_teams: list["KSprintTeam"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KTeam"]
