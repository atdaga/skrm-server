from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TaskOwnerCreate(BaseModel):
    """Schema for adding a new task owner relationship."""

    principal_id: UUID
    role: str | None = None
    meta: dict = {}


class TaskOwnerUpdate(BaseModel):
    """Schema for updating task owner relationship information."""

    role: str | None = None
    meta: dict | None = None


class TaskOwner(BaseModel):
    """Schema for task owner relationship response."""

    task_id: UUID
    principal_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TaskOwnerDetail(TaskOwner):
    """Schema for task owner relationship detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TaskOwnerList(BaseModel):
    """Schema for task owner relationship list response."""

    owners: list[TaskOwnerDetail]


__all__ = [
    "TaskOwnerCreate",
    "TaskOwnerUpdate",
    "TaskOwner",
    "TaskOwnerDetail",
    "TaskOwnerList",
]
