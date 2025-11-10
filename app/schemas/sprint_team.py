from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SprintTeamCreate(BaseModel):
    """Schema for adding a new team to a sprint."""

    team_id: UUID
    role: str | None = None
    meta: dict = {}


class SprintTeamUpdate(BaseModel):
    """Schema for updating sprint team information."""

    role: str | None = None
    meta: dict | None = None


class SprintTeam(BaseModel):
    """Schema for sprint team response."""

    sprint_id: UUID
    team_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class SprintTeamDetail(SprintTeam):
    """Schema for sprint team detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class SprintTeamList(BaseModel):
    """Schema for sprint team list response."""

    teams: list[SprintTeamDetail]


__all__ = [
    "SprintTeamCreate",
    "SprintTeamUpdate",
    "SprintTeam",
    "SprintTeamDetail",
    "SprintTeamList",
]
