from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class FeatureType(str, Enum):
    """Feature type enumeration."""

    PRODUCT = "Product"
    ENGINEERING = "Engineering"


class ReviewResult(str, Enum):
    """Review result enumeration."""

    QUEUED = "Queued"
    REVIEWING = "Reviewing"
    PASSED = "Passed"
    FAILED = "Failed"
    SKIPPED = "Skipped"


class KFeature(SQLModel, table=True):
    __tablename__ = "k_feature"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    name: str = Field(..., max_length=255)
    parent: UUID | None = Field(default=None, foreign_key="k_feature.id", index=True)
    parent_path: str | None = Field(default=None, max_length=None)
    feature_type: FeatureType = Field(...)
    summary: str | None = Field(default=None, sa_type=Text)
    notes: str | None = Field(default=None, sa_type=Text)
    guestimate: float | None = Field(default=None, gt=0)
    derived_guestimate: float | None = Field(default=None, gt=0)
    review_result: ReviewResult = Field(default=ReviewResult.QUEUED)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KFeature", "FeatureType", "ReviewResult"]
