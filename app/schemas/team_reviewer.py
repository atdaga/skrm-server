from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeamReviewerCreate(BaseModel):
    """Schema for adding a new team reviewer."""

    principal_id: UUID
    role: str | None = None
    meta: dict = {}


class TeamReviewerUpdate(BaseModel):
    """Schema for updating team reviewer information."""

    role: str | None = None
    meta: dict | None = None


class TeamReviewer(BaseModel):
    """Schema for team reviewer response."""

    team_id: UUID
    principal_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TeamReviewerDetail(TeamReviewer):
    """Schema for team reviewer detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TeamReviewerList(BaseModel):
    """Schema for team reviewer list response."""

    reviewers: list[TeamReviewerDetail]


__all__ = [
    "TeamReviewerCreate",
    "TeamReviewerUpdate",
    "TeamReviewer",
    "TeamReviewerDetail",
    "TeamReviewerList",
]
