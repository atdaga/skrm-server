from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.repr_mixin import SecureReprMixin

if TYPE_CHECKING:
    from .k_organization_principal import KOrganizationPrincipal


class KOrganization(SecureReprMixin, SQLModel, table=True):
    __tablename__ = "k_organization"
    __table_args__ = (
        UniqueConstraint("name"),
        UniqueConstraint("alias"),
    )

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    name: str = Field(..., max_length=255)
    alias: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization_principals: list["KOrganizationPrincipal"] = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KOrganization"]
