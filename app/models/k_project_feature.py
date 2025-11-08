from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_feature import KFeature
    from .k_organization import KOrganization
    from .k_project import KProject


class KProjectFeature(SQLModel, table=True):
    __tablename__ = "k_project_feature"

    project_id: UUID = Field(
        sa_column=Column(
            ForeignKey("k_project.id", ondelete="CASCADE"), primary_key=True
        )
    )
    feature_id: UUID = Field(
        sa_column=Column(
            ForeignKey("k_feature.id", ondelete="CASCADE"), primary_key=True
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
    organization: "KOrganization" = Relationship()
    project: "KProject" = Relationship(
        back_populates="project_features",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    feature: "KFeature" = Relationship(
        back_populates="feature_projects",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KProjectFeature"]
