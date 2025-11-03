from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeamCreate(BaseModel):
    """Schema for creating a new team."""

    name: str
    meta: dict = {}


class TeamUpdate(BaseModel):
    """Schema for updating team information."""

    name: str | None = None
    meta: dict | None = None


class Team(BaseModel):
    """Schema for team response."""

    id: UUID
    scope: str
    name: str
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TeamDetail(Team):
    """Schema for team detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TeamList(BaseModel):
    """Schema for team list response."""

    teams: list[TeamDetail]


__all__ = ["TeamCreate", "TeamUpdate", "Team", "TeamDetail", "TeamList"]
