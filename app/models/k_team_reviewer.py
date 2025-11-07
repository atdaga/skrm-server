from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_principal import KPrincipal
    from .k_team import KTeam


class KTeamReviewer(SQLModel, table=True):
    __tablename__ = "k_team_reviewer"

    team_id: UUID = Field(
        sa_column=Column(ForeignKey("k_team.id", ondelete="CASCADE"), primary_key=True)
    )
    principal_id: UUID = Field(
        sa_column=Column(
            ForeignKey("k_principal.id", ondelete="CASCADE"), primary_key=True
        )
    )
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    team: "KTeam" = Relationship(
        back_populates="team_reviewers",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    principal: "KPrincipal" = Relationship(
        back_populates="team_reviewer_assignments",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KTeamReviewer"]
