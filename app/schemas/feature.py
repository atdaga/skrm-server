from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.repr_mixin import SecureReprMixin

from ..models.k_feature import FeatureType, ReviewResult


class FeatureCreate(SecureReprMixin, BaseModel):
    """Schema for creating a new feature."""

    name: str
    parent: UUID | None = None
    parent_path: str | None = None
    feature_type: FeatureType
    summary: str | None = None
    details: str | None = None
    guestimate: float | None = Field(None, gt=0)
    derived_guestimate: float | None = Field(None, gt=0)
    review_result: ReviewResult | None = None
    meta: dict = {}


class FeatureUpdate(SecureReprMixin, BaseModel):
    """Schema for updating feature information."""

    name: str | None = None
    parent: UUID | None = None
    parent_path: str | None = None
    feature_type: FeatureType | None = None
    summary: str | None = None
    details: str | None = None
    guestimate: float | None = Field(None, gt=0)
    derived_guestimate: float | None = Field(None, gt=0)
    review_result: ReviewResult | None = None
    meta: dict | None = None


class Feature(SecureReprMixin, BaseModel):
    """Schema for feature response."""

    id: UUID
    org_id: UUID
    name: str
    parent: UUID | None
    parent_path: str | None
    feature_type: FeatureType
    summary: str | None
    details: str | None
    guestimate: float | None
    derived_guestimate: float | None
    review_result: ReviewResult | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class FeatureDetail(Feature):
    """Schema for feature detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class FeatureList(SecureReprMixin, BaseModel):
    """Schema for feature list response."""

    features: list[FeatureDetail]


__all__ = [
    "FeatureCreate",
    "FeatureUpdate",
    "Feature",
    "FeatureDetail",
    "FeatureList",
]
