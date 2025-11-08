from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..models.k_sprint import SprintStatus


class SprintCreate(BaseModel):
    """Schema for creating a new sprint."""

    title: str | None = None
    status: SprintStatus = SprintStatus.BACKLOG
    end_ts: datetime | None = None
    meta: dict = {}


class SprintUpdate(BaseModel):
    """Schema for updating sprint information."""

    title: str | None = None
    status: SprintStatus | None = None
    end_ts: datetime | None = None
    meta: dict | None = None


class Sprint(BaseModel):
    """Schema for sprint response."""

    id: UUID
    org_id: UUID
    title: str | None
    status: SprintStatus
    end_ts: datetime | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class SprintDetail(Sprint):
    """Schema for sprint detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class SprintList(BaseModel):
    """Schema for sprint list response."""

    sprints: list[SprintDetail]


__all__ = ["SprintCreate", "SprintUpdate", "Sprint", "SprintDetail", "SprintList"]
