from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class TaskDeploymentEnvCreate(SecureReprMixin, BaseModel):
    """Schema for adding a new task deployment environment relationship."""

    deployment_env_id: UUID
    role: str | None = None
    meta: dict = {}


class TaskDeploymentEnvUpdate(SecureReprMixin, BaseModel):
    """Schema for updating task deployment environment relationship information."""

    role: str | None = None
    meta: dict | None = None


class TaskDeploymentEnv(SecureReprMixin, BaseModel):
    """Schema for task deployment environment relationship response."""

    task_id: UUID
    deployment_env_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class TaskDeploymentEnvDetail(TaskDeploymentEnv):
    """Schema for task deployment environment relationship detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class TaskDeploymentEnvList(SecureReprMixin, BaseModel):
    """Schema for task deployment environment relationship list response."""

    deployment_envs: list[TaskDeploymentEnvDetail]


__all__ = [
    "TaskDeploymentEnvCreate",
    "TaskDeploymentEnvUpdate",
    "TaskDeploymentEnv",
    "TaskDeploymentEnvDetail",
    "TaskDeploymentEnvList",
]
