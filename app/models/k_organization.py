from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_organization_principal import KOrganizationPrincipal


class KOrganization(SQLModel, table=True):
    __tablename__ = "k_organization"
    __table_args__ = (
        UniqueConstraint("name"),
        UniqueConstraint("alias"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=255)
    alias: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization_principals: list["KOrganizationPrincipal"] = Relationship(
        back_populates="organization", cascade_delete=True
    )


__all__ = ["KOrganization"]
