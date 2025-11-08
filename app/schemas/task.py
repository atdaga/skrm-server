from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..models.k_feature import ReviewResult
from ..models.k_task import TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    summary: str | None = None
    description: str | None = None
    team_id: UUID
    guestimate: float | None = Field(None, gt=0)
    status: TaskStatus = TaskStatus.BACKLOG
    review_result: ReviewResult | None = None
    meta: dict = {}


class TaskUpdate(BaseModel):
    """Schema for updating task information."""

    summary: str | None = None
    description: str | None = None
    team_id: UUID | None = None
    guestimate: float | None = Field(None, gt=0)
    status: TaskStatus | None = None
    review_result: ReviewResult | None = None
    meta: dict | None = None


class Task(BaseModel):
    """Schema for task response."""

    id: UUID
    org_id: UUID
    summary: str | None
    description: str | None
    team_id: UUID
    guestimate: float | None
    status: TaskStatus
    review_result: ReviewResult | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TaskDetail(Task):
    """Schema for task detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TaskList(BaseModel):
    """Schema for task list response."""

    tasks: list[TaskDetail]


__all__ = [
    "TaskCreate",
    "TaskUpdate",
    "Task",
    "TaskDetail",
    "TaskList",
]
