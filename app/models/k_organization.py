from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class KOrganization(SQLModel, table=True):
    __tablename__ = "k_organization"
    __table_args__ = (
        UniqueConstraint("name"),
        UniqueConstraint("alias"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=255)
    alias: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KOrganization"]
