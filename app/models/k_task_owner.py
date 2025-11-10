from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_organization import KOrganization
    from .k_principal import KPrincipal
    from .k_task import KTask


class KTaskOwner(SQLModel, table=True):
    __tablename__ = "k_task_owner"

    task_id: UUID = Field(
        sa_column=Column(ForeignKey("k_task.id", ondelete="CASCADE"), primary_key=True)
    )
    principal_id: UUID = Field(
        sa_column=Column(
            ForeignKey("k_principal.id", ondelete="CASCADE"), primary_key=True
        )
    )
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    role: str | None = Field(default=None, max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship()
    task: "KTask" = Relationship(
        back_populates="task_owners",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    principal: "KPrincipal" = Relationship(
        back_populates="task_owner_assignments",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KTaskOwner"]
