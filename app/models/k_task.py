from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Text
from sqlmodel import Column, Field, Relationship, SQLModel, String

from app.core.repr_mixin import SecureReprMixin

from .k_feature import ReviewResult

if TYPE_CHECKING:
    from .k_organization import KOrganization
    from .k_sprint_task import KSprintTask
    from .k_task_deployment_env import KTaskDeploymentEnv
    from .k_task_feature import KTaskFeature
    from .k_task_owner import KTaskOwner
    from .k_task_reviewer import KTaskReviewer
    from .k_team import KTeam


class TaskStatus(StrEnum):
    """Task status enumeration."""

    BACKLOG = "Backlog"
    ON_DECK = "OnDeck"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    DEPLOYED = "Deployed"
    REVIEW = "Review"
    DONE = "Done"
    ARCHIVED = "Archived"


class KTask(SecureReprMixin, SQLModel, table=True):
    __tablename__ = "k_task"

    id: UUID = Field(primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    summary: str | None = Field(default=None, sa_type=Text)
    description: str | None = Field(default=None, sa_type=Text)
    team_id: UUID = Field(foreign_key="k_team.id", index=True)
    guestimate: float | None = Field(default=None, gt=0)
    status: TaskStatus = Field(default=TaskStatus.BACKLOG, sa_column=Column(String))
    review_result: ReviewResult | None = Field(default=None, sa_column=Column(String))
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    organization: "KOrganization" = Relationship()
    team: "KTeam" = Relationship()
    task_deployment_envs: list["KTaskDeploymentEnv"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"passive_deletes": True}
    )
    task_features: list["KTaskFeature"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"passive_deletes": True}
    )
    task_owners: list["KTaskOwner"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"passive_deletes": True}
    )
    task_reviewers: list["KTaskReviewer"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"passive_deletes": True}
    )
    sprint_tasks: list["KSprintTask"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"passive_deletes": True}
    )


__all__ = ["KTask", "TaskStatus"]
