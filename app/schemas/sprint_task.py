from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class SprintTaskCreate(SecureReprMixin, BaseModel):
    """Schema for adding a new task to a sprint."""

    task_id: UUID
    role: str | None = None
    meta: dict = {}


class SprintTaskUpdate(SecureReprMixin, BaseModel):
    """Schema for updating sprint task information."""

    role: str | None = None
    meta: dict | None = None


class SprintTask(SecureReprMixin, BaseModel):
    """Schema for sprint task response."""

    sprint_id: UUID
    task_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class SprintTaskDetail(SprintTask):
    """Schema for sprint task detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class SprintTaskList(SecureReprMixin, BaseModel):
    """Schema for sprint task list response."""

    tasks: list[SprintTaskDetail]


__all__ = [
    "SprintTaskCreate",
    "SprintTaskUpdate",
    "SprintTask",
    "SprintTaskDetail",
    "SprintTaskList",
]
