from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocCreate(BaseModel):
    """Schema for creating a new doc."""

    name: str
    description: str | None = None
    content: str
    meta: dict = {}


class DocUpdate(BaseModel):
    """Schema for updating doc information."""

    name: str | None = None
    description: str | None = None
    content: str | None = None
    meta: dict | None = None


class Doc(BaseModel):
    """Schema for doc response."""

    id: UUID
    org_id: UUID
    name: str
    description: str | None
    content: str
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class DocDetail(Doc):
    """Schema for doc detailed response with audit fields."""

    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class DocList(BaseModel):
    """Schema for doc list response."""

    docs: list[DocDetail]


__all__ = ["DocCreate", "DocUpdate", "Doc", "DocDetail", "DocList"]
