from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .k_task_deployment_env import KTaskDeploymentEnv


class KDeploymentEnv(SQLModel, table=True):
    __tablename__ = "k_deployment_env"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    name: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    task_deployment_envs: list["KTaskDeploymentEnv"] = Relationship(
        back_populates="deployment_env",
        sa_relationship_kwargs={"passive_deletes": True},
    )


__all__ = ["KDeploymentEnv"]
