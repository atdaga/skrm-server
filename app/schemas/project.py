from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str
    description: str | None = None
    meta: dict = {}


class ProjectUpdate(BaseModel):
    """Schema for updating project information."""

    name: str | None = None
    description: str | None = None
    meta: dict | None = None


class Project(BaseModel):
    """Schema for project response."""

    id: UUID
    org_id: UUID
    name: str
    description: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(Project):
    """Schema for project detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class ProjectList(BaseModel):
    """Schema for project list response."""

    projects: list[ProjectDetail]


__all__ = ["ProjectCreate", "ProjectUpdate", "Project", "ProjectDetail", "ProjectList"]
