from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class ProjectTeamCreate(SecureReprMixin, BaseModel):
    """Schema for adding a new team to a project."""

    team_id: UUID
    role: str | None = None
    meta: dict = {}


class ProjectTeamUpdate(SecureReprMixin, BaseModel):
    """Schema for updating project team information."""

    role: str | None = None
    meta: dict | None = None


class ProjectTeam(SecureReprMixin, BaseModel):
    """Schema for project team response."""

    project_id: UUID
    team_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class ProjectTeamDetail(ProjectTeam):
    """Schema for project team detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class ProjectTeamList(SecureReprMixin, BaseModel):
    """Schema for project team list response."""

    teams: list[ProjectTeamDetail]


__all__ = [
    "ProjectTeamCreate",
    "ProjectTeamUpdate",
    "ProjectTeam",
    "ProjectTeamDetail",
    "ProjectTeamList",
]
