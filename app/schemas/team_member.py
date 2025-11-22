from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class TeamMemberCreate(SecureReprMixin, BaseModel):
    """Schema for adding a new team member."""

    principal_id: UUID
    role: str | None = None
    meta: dict = {}


class TeamMemberUpdate(SecureReprMixin, BaseModel):
    """Schema for updating team member information."""

    role: str | None = None
    meta: dict | None = None


class TeamMember(SecureReprMixin, BaseModel):
    """Schema for team member response."""

    team_id: UUID
    principal_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TeamMemberDetail(TeamMember):
    """Schema for team member detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TeamMemberList(SecureReprMixin, BaseModel):
    """Schema for team member list response."""

    members: list[TeamMemberDetail]


__all__ = [
    "TeamMemberCreate",
    "TeamMemberUpdate",
    "TeamMember",
    "TeamMemberDetail",
    "TeamMemberList",
]
