from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class DeploymentEnvCreate(SecureReprMixin, BaseModel):
    """Schema for creating a new deployment environment."""

    name: str
    meta: dict = {}


class DeploymentEnvUpdate(SecureReprMixin, BaseModel):
    """Schema for updating deployment environment information."""

    name: str | None = None
    meta: dict | None = None


class DeploymentEnv(SecureReprMixin, BaseModel):
    """Schema for deployment environment response."""

    id: UUID
    org_id: UUID
    name: str
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class DeploymentEnvDetail(DeploymentEnv):
    """Schema for deployment environment detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class DeploymentEnvList(SecureReprMixin, BaseModel):
    """Schema for deployment environment list response."""

    deployment_envs: list[DeploymentEnvDetail]


__all__ = [
    "DeploymentEnvCreate",
    "DeploymentEnvUpdate",
    "DeploymentEnv",
    "DeploymentEnvDetail",
    "DeploymentEnvList",
]
