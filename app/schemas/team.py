from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class TeamCreate(SecureReprMixin, BaseModel):
    """Schema for creating a new team."""

    name: str
    meta: dict = {}


class TeamUpdate(SecureReprMixin, BaseModel):
    """Schema for updating team information."""

    name: str | None = None
    meta: dict | None = None


class Team(SecureReprMixin, BaseModel):
    """Schema for team response."""

    id: UUID
    org_id: UUID
    name: str
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TeamDetail(Team):
    """Schema for team detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TeamList(SecureReprMixin, BaseModel):
    """Schema for team list response."""

    teams: list[TeamDetail]


__all__ = ["TeamCreate", "TeamUpdate", "Team", "TeamDetail", "TeamList"]
