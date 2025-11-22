from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class TeamReviewerCreate(SecureReprMixin, BaseModel):
    """Schema for adding a new team reviewer."""

    principal_id: UUID
    role: str | None = None
    meta: dict = {}


class TeamReviewerUpdate(SecureReprMixin, BaseModel):
    """Schema for updating team reviewer information."""

    role: str | None = None
    meta: dict | None = None


class TeamReviewer(SecureReprMixin, BaseModel):
    """Schema for team reviewer response."""

    team_id: UUID
    principal_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TeamReviewerDetail(TeamReviewer):
    """Schema for team reviewer detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TeamReviewerList(SecureReprMixin, BaseModel):
    """Schema for team reviewer list response."""

    reviewers: list[TeamReviewerDetail]


__all__ = [
    "TeamReviewerCreate",
    "TeamReviewerUpdate",
    "TeamReviewer",
    "TeamReviewerDetail",
    "TeamReviewerList",
]
