from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_organization_principal import KOrganizationPrincipal
    from .k_task_owner import KTaskOwner
    from .k_task_reviewer import KTaskReviewer
    from .k_team_member import KTeamMember
    from .k_team_reviewer import KTeamReviewer


class KPrincipal(SQLModel, table=True):
    __tablename__ = "k_principal"
    __table_args__ = (UniqueConstraint("scope", "username"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scope: str = Field(default="global", max_length=255)
    username: str = Field(..., max_length=255)
    primary_email: str = Field(..., max_length=255)
    primary_email_verified: bool = Field(default=False)
    primary_phone: str | None = Field(default=None, max_length=255)
    primary_phone_verified: bool = Field(default=False)
    human: bool = Field(default=True)
    enabled: bool = Field(default=True)
    time_zone: str = Field(default="UTC", max_length=255)
    name_prefix: str | None = Field(default=None, max_length=255)
    first_name: str = Field(..., max_length=255)
    middle_name: str | None = Field(default=None, max_length=255)
    last_name: str = Field(..., max_length=255)
    name_suffix: str | None = Field(default=None, max_length=255)
    display_name: str = Field(..., max_length=255)
    default_locale: str = Field(default="en", max_length=255)
    system_role: str = Field(default="system_user")
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization_memberships: list["KOrganizationPrincipal"] = Relationship(
        back_populates="principal",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    team_memberships: list["KTeamMember"] = Relationship(
        back_populates="principal",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    team_reviewer_assignments: list["KTeamReviewer"] = Relationship(
        back_populates="principal",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    task_owner_assignments: list["KTaskOwner"] = Relationship(
        back_populates="principal",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    task_reviewer_assignments: list["KTaskReviewer"] = Relationship(
        back_populates="principal",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KPrincipal"]
