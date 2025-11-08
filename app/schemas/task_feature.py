from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskFeatureCreate(BaseModel):
    """Schema for adding a new task feature relationship."""

    feature_id: UUID
    role: str | None = None
    meta: dict = {}


class TaskFeatureUpdate(BaseModel):
    """Schema for updating task feature relationship information."""

    role: str | None = None
    meta: dict | None = None


class TaskFeature(BaseModel):
    """Schema for task feature relationship response."""

    task_id: UUID
    feature_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TaskFeatureDetail(TaskFeature):
    """Schema for task feature relationship detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TaskFeatureList(BaseModel):
    """Schema for task feature relationship list response."""

    features: list[TaskFeatureDetail]


__all__ = [
    "TaskFeatureCreate",
    "TaskFeatureUpdate",
    "TaskFeature",
    "TaskFeatureDetail",
    "TaskFeatureList",
]
