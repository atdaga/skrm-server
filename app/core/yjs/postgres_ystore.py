"""PostgreSQL-backed Y.js document store.

This module provides a custom YStore implementation that persists Y.js updates
to PostgreSQL using the k_doc_yupdate table, integrated with the existing
SQLAlchemy async database infrastructure.

The store delegates all database operations to the logic layer
(app.logic.v1.yjs_collab) to maintain the api -> logic -> repository pattern.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from logging import Logger
from uuid import UUID

from pycrdt.store import BaseYStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.logic.v1 import yjs_collab

logger = get_logger(__name__)


class PostgresYStore(BaseYStore):
    """PostgreSQL-backed Y.js document store using k_doc_yupdate table.

    This store persists Y.js updates to the PostgreSQL database, allowing
    documents to be reconstructed across server restarts and enabling
    multiple server instances to share document state.

    All database operations are delegated to the logic layer.

    Attributes:
        doc_id: The document ID (foreign key to k_doc)
        org_id: The organization ID for audit trail
        user_id: The user ID for audit trail
        document_ttl: Time in seconds before old updates are compacted (None = never)
    """

    version = 2  # Store format version

    def __init__(
        self,
        path: str,  # Required by base class, we use doc_id instead
        metadata_callback: Callable[[], Awaitable[bytes] | bytes] | None = None,
        log: Logger | None = None,
        *,
        doc_id: UUID,
        org_id: UUID,
        user_id: UUID,
        db_session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]],
        document_ttl: int | None = 3600,  # 1 hour default
    ) -> None:
        """Initialize the PostgreSQL Y.js store.

        Args:
            path: Document path (required by base class, stored but not used)
            metadata_callback: Optional callback to generate metadata for each update
            log: Optional logger instance
            doc_id: The document ID (foreign key to k_doc)
            org_id: The organization ID for audit trail
            user_id: The user ID for audit trail (creator of updates)
            db_session_factory: Factory function to create database sessions
            document_ttl: Time in seconds before old updates are compacted.
                         Set to None to disable automatic compaction.
        """
        self.path = path
        self.metadata_callback = metadata_callback
        self.log = log or logger
        self.doc_id = doc_id
        self.org_id = org_id
        self.user_id = user_id
        self._db_session_factory = db_session_factory
        self.document_ttl = document_ttl

    async def read(
        self,
    ) -> AsyncIterator[tuple[bytes, bytes, float]]:  # pragma: no cover
        """Read all Y.js updates for this document.

        Yields:
            Tuples of (update_bytes, metadata_bytes, timestamp) for each stored update,
            ordered by timestamp ascending.
        """
        async with self._db_session_factory() as db:
            updates = await yjs_collab.read_yupdates(self.doc_id, db)
            for yupdate, meta, timestamp in updates:
                yield (yupdate, meta or b"", timestamp)

    async def write(self, data: bytes) -> None:  # pragma: no cover
        """Write a Y.js update to the database.

        Args:
            data: The Y.js update bytes to store
        """
        # Get metadata if callback is configured
        metadata_bytes: bytes | None = None
        if self.metadata_callback:
            metadata_result = self.metadata_callback()
            if isinstance(metadata_result, bytes):
                metadata_bytes = metadata_result
            else:
                metadata_bytes = await metadata_result

        async with self._db_session_factory() as db:
            await yjs_collab.write_yupdate(
                doc_id=self.doc_id,
                org_id=self.org_id,
                user_id=self.user_id,
                yupdate=data,
                yupdate_meta=metadata_bytes,
                db=db,
            )

            self.log.debug(  # type: ignore[call-arg]
                "Wrote Y.js update",
                doc_id=str(self.doc_id),
                size=len(data),
            )

            # Check if compaction is needed
            if self.document_ttl is not None:
                await self._maybe_compact(db)

    async def _maybe_compact(self, db: AsyncSession) -> None:  # pragma: no cover
        """Compact old updates into a single snapshot if threshold exceeded.

        This method checks the number of updates and compacts them if needed.

        Args:
            db: Database session to use
        """
        # Compaction threshold: compact if more than 100 updates
        compaction_threshold = 100

        update_count = await yjs_collab.get_doc_update_count(self.doc_id, db)
        if update_count <= compaction_threshold:
            return

        self.log.info(  # type: ignore[call-arg]
            "Compacting Y.js updates",
            doc_id=str(self.doc_id),
            update_count=update_count,
        )

        # Use the logic layer's compact function
        await yjs_collab.compact_doc_updates(self.doc_id, self.user_id, db)

    async def get_document_state(self) -> bytes | None:  # pragma: no cover
        """Get the current document state as a single update.

        This is useful for initializing new clients with the full document state.

        Returns:
            The merged document state as bytes, or None if no updates exist.
        """
        async with self._db_session_factory() as db:
            return await yjs_collab.get_document_state(self.doc_id, db)


__all__ = ["PostgresYStore"]
