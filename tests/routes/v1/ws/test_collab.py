"""Tests for Y.js collaboration WebSocket endpoint."""

from uuid import UUID, uuid7

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KDoc, KDocYupdate


@pytest.fixture
async def test_doc(
    async_session: AsyncSession, test_organization, test_user_id: UUID
) -> KDoc:
    """Create a test document for WebSocket collaboration testing."""
    doc = KDoc(
        org_id=test_organization.id,
        name="Test Document",
        description="A test document for collaboration",
        content="",
        meta={},
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(doc)
    await async_session.commit()
    await async_session.refresh(doc)
    return doc


@pytest.fixture
async def test_doc_without_membership(
    async_session: AsyncSession,
    test_organization_without_membership,
    test_user_id: UUID,
) -> KDoc:
    """Create a test document in an organization the user is NOT a member of."""
    doc = KDoc(
        org_id=test_organization_without_membership.id,
        name="Unauthorized Document",
        description="A document the user cannot access",
        content="",
        meta={},
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(doc)
    await async_session.commit()
    await async_session.refresh(doc)
    return doc


class TestYjsWebsocketEndpoint:
    """Tests for the Y.js WebSocket collaboration endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_invalid_token_rejected(
        self, async_session: AsyncSession, test_doc: KDoc
    ):
        """Test that WebSocket connection with invalid token is rejected."""
        from unittest.mock import AsyncMock, patch

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routes.v1.ws import collab

        # Create a minimal app with the WebSocket route
        app = FastAPI()
        app.include_router(collab.router)

        # Mock the token validation to return None (invalid token)
        with patch(
            "app.routes.v1.ws.collab.validate_websocket_token",
            new_callable=AsyncMock,
            return_value=None,
        ):
            client = TestClient(app)
            with pytest.raises(Exception):  # noqa: B017
                # WebSocket should be closed with error code
                with client.websocket_connect(f"/{test_doc.id}?token=invalid"):
                    pass

    @pytest.mark.asyncio
    async def test_websocket_document_not_found(
        self, async_session: AsyncSession, test_user_id: UUID
    ):
        """Test that WebSocket connection for non-existent document is rejected."""
        from unittest.mock import AsyncMock, patch

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routes.v1.ws import collab

        app = FastAPI()
        app.include_router(collab.router)

        fake_doc_id = uuid7()

        # Mock token validation to return a valid user ID
        with (
            patch(
                "app.routes.v1.ws.collab.validate_websocket_token",
                new_callable=AsyncMock,
                return_value=test_user_id,
            ),
            patch(
                "app.routes.v1.ws.collab.get_db_session",
                return_value=async_session,
            ),
        ):
            client = TestClient(app)
            with pytest.raises(Exception):  # noqa: B017
                # WebSocket should be closed with 4004 code
                with client.websocket_connect(f"/{fake_doc_id}?token=valid"):
                    pass


class TestKDocYupdateModel:
    """Tests for the KDocYupdate model."""

    @pytest.mark.asyncio
    async def test_create_yupdate(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test creating a Y.js update record."""
        import time

        yupdate = KDocYupdate(
            doc_id=test_doc.id,
            org_id=test_doc.org_id,
            yupdate=b"\x00\x01\x02",  # Sample Y.js update bytes
            yupdate_meta=None,
            timestamp=time.time(),
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(yupdate)
        await async_session.commit()
        await async_session.refresh(yupdate)

        assert yupdate.id is not None
        assert yupdate.doc_id == test_doc.id
        assert yupdate.org_id == test_doc.org_id
        assert yupdate.yupdate == b"\x00\x01\x02"

    @pytest.mark.asyncio
    async def test_yupdate_with_metadata(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test creating a Y.js update with metadata."""
        import time

        yupdate = KDocYupdate(
            doc_id=test_doc.id,
            org_id=test_doc.org_id,
            yupdate=b"\x00\x01\x02",
            yupdate_meta=b"metadata",
            timestamp=time.time(),
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(yupdate)
        await async_session.commit()
        await async_session.refresh(yupdate)

        assert yupdate.yupdate_meta == b"metadata"

    @pytest.mark.asyncio
    async def test_multiple_yupdates_for_doc(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test that multiple Y.js updates can be stored for a document."""
        import time

        from sqlalchemy import select

        # Create multiple updates
        for i in range(3):
            yupdate = KDocYupdate(
                doc_id=test_doc.id,
                org_id=test_doc.org_id,
                yupdate=bytes([i]),
                timestamp=time.time() + i,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(yupdate)

        await async_session.commit()

        # Query updates
        stmt = (
            select(KDocYupdate)
            .where(
                KDocYupdate.doc_id == test_doc.id,
                KDocYupdate.deleted_at.is_(None),
            )
            .order_by(KDocYupdate.timestamp)
        )
        result = await async_session.execute(stmt)
        updates = list(result.scalars())

        assert len(updates) == 3
        for i, update in enumerate(updates):
            assert update.yupdate == bytes([i])


class TestYjsCollabLogic:
    """Tests for Y.js collaboration business logic."""

    @pytest.mark.asyncio
    async def test_get_doc_by_id(self, async_session: AsyncSession, test_doc: KDoc):
        """Test retrieving a document by ID."""
        from app.logic.v1.yjs_collab import get_doc_by_id

        doc = await get_doc_by_id(test_doc.id, async_session)
        assert doc is not None
        assert doc.id == test_doc.id
        assert doc.name == "Test Document"

    @pytest.mark.asyncio
    async def test_get_doc_by_id_not_found(self, async_session: AsyncSession):
        """Test that non-existent document returns None."""
        from app.logic.v1.yjs_collab import get_doc_by_id

        doc = await get_doc_by_id(uuid7(), async_session)
        assert doc is None

    @pytest.mark.asyncio
    async def test_get_doc_for_collab_success(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test getting document for collaboration with valid access."""
        from app.logic.v1.yjs_collab import get_doc_for_collab

        doc = await get_doc_for_collab(test_doc.id, test_user_id, async_session)
        assert doc is not None
        assert doc.id == test_doc.id
        assert doc.name == "Test Document"

    @pytest.mark.asyncio
    async def test_get_doc_for_collab_not_found(
        self, async_session: AsyncSession, test_user_id: UUID
    ):
        """Test getting non-existent document for collaboration returns None."""
        from app.logic.v1.yjs_collab import get_doc_for_collab

        doc = await get_doc_for_collab(uuid7(), test_user_id, async_session)
        assert doc is None

    @pytest.mark.asyncio
    async def test_get_doc_for_collab_unauthorized(
        self,
        async_session: AsyncSession,
        test_doc_without_membership: KDoc,
        test_user_id: UUID,
    ):
        """Test getting document for collaboration without membership raises exception."""
        from app.core.exceptions.domain_exceptions import (
            UnauthorizedOrganizationAccessException,
        )
        from app.logic.v1.yjs_collab import get_doc_for_collab

        with pytest.raises(UnauthorizedOrganizationAccessException):
            await get_doc_for_collab(
                test_doc_without_membership.id, test_user_id, async_session
            )

    @pytest.mark.asyncio
    async def test_read_yupdates(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test reading Y.js updates for a document."""
        import time

        from app.logic.v1.yjs_collab import read_yupdates

        # Initially no updates
        updates = await read_yupdates(test_doc.id, async_session)
        assert updates == []

        # Add some updates
        base_time = time.time()
        for i in range(3):
            yupdate = KDocYupdate(
                doc_id=test_doc.id,
                org_id=test_doc.org_id,
                yupdate=bytes([i]),
                yupdate_meta=b"meta" if i == 1 else None,
                timestamp=base_time + i,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(yupdate)
        await async_session.commit()

        # Read updates
        updates = await read_yupdates(test_doc.id, async_session)
        assert len(updates) == 3
        # Verify order by timestamp
        assert updates[0][0] == bytes([0])
        assert updates[1][0] == bytes([1])
        assert updates[2][0] == bytes([2])
        # Verify metadata
        assert updates[0][1] is None
        assert updates[1][1] == b"meta"
        assert updates[2][1] is None

    @pytest.mark.asyncio
    async def test_write_yupdate(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test writing a Y.js update to the database."""
        from app.logic.v1.yjs_collab import get_doc_update_count, write_yupdate

        # Initially no updates
        count = await get_doc_update_count(test_doc.id, async_session)
        assert count == 0

        # Write an update
        await write_yupdate(
            doc_id=test_doc.id,
            org_id=test_doc.org_id,
            user_id=test_user_id,
            yupdate=b"\x00\x01\x02",
            yupdate_meta=b"test-meta",
            db=async_session,
        )

        # Verify update was written
        count = await get_doc_update_count(test_doc.id, async_session)
        assert count == 1

    @pytest.mark.asyncio
    async def test_write_yupdate_without_metadata(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test writing a Y.js update without metadata."""
        from app.logic.v1.yjs_collab import read_yupdates, write_yupdate

        # Write an update without metadata
        await write_yupdate(
            doc_id=test_doc.id,
            org_id=test_doc.org_id,
            user_id=test_user_id,
            yupdate=b"\x00\x01\x02",
            yupdate_meta=None,
            db=async_session,
        )

        # Verify update was written
        updates = await read_yupdates(test_doc.id, async_session)
        assert len(updates) == 1
        assert updates[0][0] == b"\x00\x01\x02"
        assert updates[0][1] is None

    @pytest.mark.asyncio
    async def test_get_doc_update_count(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test counting Y.js updates for a document."""
        import time

        from app.logic.v1.yjs_collab import get_doc_update_count

        # Initially no updates
        count = await get_doc_update_count(test_doc.id, async_session)
        assert count == 0

        # Add some updates
        for i in range(5):
            yupdate = KDocYupdate(
                doc_id=test_doc.id,
                org_id=test_doc.org_id,
                yupdate=bytes([i]),
                timestamp=time.time() + i,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(yupdate)
        await async_session.commit()

        count = await get_doc_update_count(test_doc.id, async_session)
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_document_state(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test getting merged document state."""
        import time

        from pycrdt import Doc, Text

        from app.logic.v1.yjs_collab import get_document_state

        # Create a real Y.js document and generate updates
        doc1 = Doc()
        doc1.get("text", type=Text)  # Use Text type for Y.js

        # Get initial state update
        initial_update = doc1.get_update()

        # Store the update
        yupdate = KDocYupdate(
            doc_id=test_doc.id,
            org_id=test_doc.org_id,
            yupdate=initial_update,
            timestamp=time.time(),
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(yupdate)
        await async_session.commit()

        # Get document state
        state = await get_document_state(test_doc.id, async_session)
        assert state is not None
        assert isinstance(state, bytes)

    @pytest.mark.asyncio
    async def test_get_document_state_empty(
        self, async_session: AsyncSession, test_doc: KDoc
    ):
        """Test getting document state when no updates exist."""
        from app.logic.v1.yjs_collab import get_document_state

        state = await get_document_state(test_doc.id, async_session)
        assert state is None

    @pytest.mark.asyncio
    async def test_delete_doc_updates(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test deleting all Y.js updates for a document."""
        import time

        from app.logic.v1.yjs_collab import delete_doc_updates, get_doc_update_count

        # Add some updates
        for i in range(3):
            yupdate = KDocYupdate(
                doc_id=test_doc.id,
                org_id=test_doc.org_id,
                yupdate=bytes([i]),
                timestamp=time.time() + i,
                created_by=test_user_id,
                last_modified_by=test_user_id,
            )
            async_session.add(yupdate)
        await async_session.commit()

        # Verify updates exist
        count = await get_doc_update_count(test_doc.id, async_session)
        assert count == 3

        # Delete updates
        deleted = await delete_doc_updates(test_doc.id, async_session)
        assert deleted == 3

        # Verify updates are gone
        count = await get_doc_update_count(test_doc.id, async_session)
        assert count == 0


class TestPostgresYStore:
    """Tests for the PostgreSQL Y.js store."""

    @pytest.mark.asyncio
    async def test_store_write_and_read(
        self, async_session: AsyncSession, test_doc: KDoc, test_user_id: UUID
    ):
        """Test writing and reading updates through the store."""
        from contextlib import asynccontextmanager

        from app.core.yjs.postgres_ystore import PostgresYStore

        # Create a mock db_session_factory that returns our test session
        @asynccontextmanager
        async def mock_db_session_factory():
            yield async_session

        # Create store with the new required db_session_factory parameter
        store = PostgresYStore(
            path=str(test_doc.id),
            doc_id=test_doc.id,
            org_id=test_doc.org_id,
            user_id=test_user_id,
            db_session_factory=mock_db_session_factory,
            document_ttl=None,  # Disable compaction for test
        )

        # Verify store was created with correct attributes
        assert store.doc_id == test_doc.id
        assert store.org_id == test_doc.org_id
        assert store.user_id == test_user_id
        assert store.document_ttl is None


class TestYjsWebsocketManager:
    """Tests for the Y.js WebSocket manager."""

    @pytest.mark.asyncio
    async def test_manager_start_stop(self):
        """Test starting and stopping the WebSocket manager."""
        from app.core.yjs.websocket_manager import YjsWebsocketManager

        manager = YjsWebsocketManager()

        # Initially not started
        assert manager._websocket_server is None

        # Start
        await manager.start()
        assert manager._websocket_server is not None

        # Double start should log warning but not fail
        await manager.start()

        # Stop
        await manager.stop()
        assert manager._websocket_server is None

        # Double stop should not fail
        await manager.stop()

    @pytest.mark.asyncio
    async def test_manager_room_count(self):
        """Test room counting in WebSocket manager."""
        from app.core.yjs.websocket_manager import YjsWebsocketManager

        manager = YjsWebsocketManager()
        await manager.start()

        try:
            assert manager.get_room_count() == 0
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_manager_has_room(self):
        """Test checking if a room exists."""
        from app.core.yjs.websocket_manager import YjsWebsocketManager

        manager = YjsWebsocketManager()
        await manager.start()

        try:
            doc_id = uuid7()
            assert manager.has_room(doc_id) is False
        finally:
            await manager.stop()


class TestConnectionManager:
    """Tests for the generic WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_connection_manager_connect_disconnect(self):
        """Test connecting and disconnecting WebSocket connections."""
        from unittest.mock import AsyncMock, MagicMock

        from app.core.websocket.manager import ConnectionManager

        manager = ConnectionManager()

        # Create mock WebSocket
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Connect
        await manager.connect("test-channel", mock_ws)
        mock_ws.accept.assert_called_once()
        assert manager.get_connection_count("test-channel") == 1
        assert manager.get_total_connections() == 1

        # Disconnect
        manager.disconnect("test-channel", mock_ws)
        assert manager.get_connection_count("test-channel") == 0
        assert manager.get_total_connections() == 0

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """Test broadcasting messages to all connections in a channel."""
        from unittest.mock import AsyncMock, MagicMock

        from app.core.websocket.manager import ConnectionManager

        manager = ConnectionManager()

        # Create mock WebSockets
        mock_ws1 = MagicMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock()

        mock_ws2 = MagicMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock()

        # Connect both
        await manager.connect("test-channel", mock_ws1)
        await manager.connect("test-channel", mock_ws2)

        # Broadcast
        message = {"type": "test", "data": "hello"}
        await manager.broadcast("test-channel", message)

        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_handles_errors(self):
        """Test that broadcast handles failed sends gracefully."""
        from unittest.mock import AsyncMock, MagicMock

        from app.core.websocket.manager import ConnectionManager

        manager = ConnectionManager()

        # Create mock WebSocket that fails on send
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.connect("test-channel", mock_ws)
        assert manager.get_connection_count("test-channel") == 1

        # Broadcast should handle the error and remove the failed connection
        await manager.broadcast("test-channel", {"type": "test"})
        assert manager.get_connection_count("test-channel") == 0
