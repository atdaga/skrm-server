from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field


class KTeam(SQLModel, table=True):
    __tablename__ = "k_team"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=255)
    meta: dict = Field(default_factory=dict, sa_type=JSON)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID


__all__ = ["KTeam"]
