from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import JSON, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.repr_mixin import SecureReprMixin

if TYPE_CHECKING:
    from .k_feature_doc import KFeatureDoc
    from .k_organization import KOrganization


class KDoc(SecureReprMixin, SQLModel, table=True):
    __tablename__ = "k_doc"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    name: str = Field(..., max_length=255)
    description: str | None = Field(default=None, max_length=255)
    content: str = Field(..., sa_type=Text)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship()
    feature_docs: list["KFeatureDoc"] = Relationship(
        back_populates="doc",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KDoc"]
