from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from .k_feature import ReviewResult


class TaskStatus(str, Enum):
    """Task status enumeration."""

    BACKLOG = "Backlog"
    ON_DECK = "OnDeck"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    DEPLOYED = "Deployed"
    REVIEW = "Review"
    DONE = "Done"
    ARCHIVED = "Archived"


class KTask(SQLModel, table=True):
    __tablename__ = "k_task"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    name: str = Field(..., max_length=255)
    summary: str | None = Field(default=None, sa_type=Text)
    description: str | None = Field(default=None, sa_type=Text)
    team_id: UUID = Field(foreign_key="k_team.id", index=True)
    guestimate: float | None = Field(default=None, gt=0)
    status: TaskStatus = Field(default=TaskStatus.BACKLOG)
    review_result: ReviewResult | None = Field(default=None)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KTask", "TaskStatus"]
