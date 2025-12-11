from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import Index, LargeBinary
from sqlmodel import Field, Relationship, SQLModel

from app.core.repr_mixin import SecureReprMixin

if TYPE_CHECKING:
    from .k_doc import KDoc
    from .k_organization import KOrganization


class KDocYupdate(SecureReprMixin, SQLModel, table=True):
    """Stores Y.js binary updates for document collaboration.

    Each document (k_doc) can have multiple Y.js updates that represent
    the collaborative editing history. Updates are stored with timestamps
    for ordering and can be compacted periodically to reduce storage.
    """

    __tablename__ = "k_doc_yupdate"
    __table_args__ = (Index("idx_doc_yupdate_doc_timestamp", "doc_id", "timestamp"),)

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    doc_id: UUID = Field(foreign_key="k_doc.id", index=True)
    org_id: UUID = Field(foreign_key="k_organization.id", index=True)
    yupdate: bytes = Field(..., sa_type=LargeBinary)
    yupdate_meta: bytes | None = Field(default=None, sa_type=LargeBinary)
    timestamp: float = Field(...)  # Unix timestamp (time.time())

    # Audit fields
    deleted_at: datetime | None = Field(default=None)
    created: datetime = Field(default_factory=datetime.now)
    created_by: UUID
    last_modified: datetime = Field(default_factory=datetime.now)
    last_modified_by: UUID

    # Relationships
    doc: "KDoc" = Relationship(back_populates="yupdates")
    organization: "KOrganization" = Relationship()


__all__ = ["KDocYupdate"]
