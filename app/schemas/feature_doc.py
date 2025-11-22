from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import SecureReprMixin


class FeatureDocCreate(SecureReprMixin, BaseModel):
    """Schema for adding a new feature doc relationship."""

    doc_id: UUID
    role: str | None = None
    meta: dict = {}


class FeatureDocUpdate(SecureReprMixin, BaseModel):
    """Schema for updating feature doc relationship information."""

    role: str | None = None
    meta: dict | None = None


class FeatureDoc(SecureReprMixin, BaseModel):
    """Schema for feature doc relationship response."""

    feature_id: UUID
    doc_id: UUID
    org_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class FeatureDocDetail(FeatureDoc):
    """Schema for feature doc relationship detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class FeatureDocList(SecureReprMixin, BaseModel):
    """Schema for feature doc relationship list response."""

    docs: list[FeatureDocDetail]


__all__ = [
    "FeatureDocCreate",
    "FeatureDocUpdate",
    "FeatureDoc",
    "FeatureDocDetail",
    "FeatureDocList",
]
