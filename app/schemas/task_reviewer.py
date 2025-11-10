from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskReviewerCreate(BaseModel):
    """Schema for adding a new task reviewer relationship."""

    principal_id: UUID
    role: str | None = None
    meta: dict = {}


class TaskReviewerUpdate(BaseModel):
    """Schema for updating task reviewer relationship information."""

    role: str | None = None
    meta: dict | None = None


class TaskReviewer(BaseModel):
    """Schema for task reviewer relationship response."""

    task_id: UUID
    principal_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TaskReviewerDetail(TaskReviewer):
    """Schema for task reviewer relationship detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TaskReviewerList(BaseModel):
    """Schema for task reviewer relationship list response."""

    reviewers: list[TaskReviewerDetail]


__all__ = [
    "TaskReviewerCreate",
    "TaskReviewerUpdate",
    "TaskReviewer",
    "TaskReviewerDetail",
    "TaskReviewerList",
]
