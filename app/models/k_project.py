from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_organization import KOrganization
    from .k_project_feature import KProjectFeature
    from .k_project_team import KProjectTeam


class KProject(SQLModel, table=True):
    __tablename__ = "k_project"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    name: str = Field(..., max_length=255)
    description: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship()
    project_teams: list["KProjectTeam"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    project_features: list["KProjectFeature"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KProject"]
