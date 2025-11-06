from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_organization import KOrganization
    from .k_principal import KPrincipal


class KOrganizationPrincipal(SQLModel, table=True):
    __tablename__ = "k_organization_principal"

    org_id: UUID = Field(
        sa_column=Column(
            ForeignKey("k_organization.id", ondelete="CASCADE"), primary_key=True
        )
    )
    principal_id: UUID = Field(foreign_key="k_principal.id", primary_key=True)
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship(
        back_populates="organization_principals"
    )
    principal: "KPrincipal" = Relationship(back_populates="organization_memberships")


__all__ = ["KOrganizationPrincipal"]
