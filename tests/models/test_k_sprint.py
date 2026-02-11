"""Unit tests for KSprint model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_sprint import KSprint, SprintStatus
from tests.conftest import get_test_org_id


class TestKSprintModel:
    """Test suite for KSprint model."""

    @pytest.mark.asyncio
    async def test_create_sprint_with_required_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a sprint with only required fields."""
        sprint = KSprint(
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.id is not None
        assert isinstance(sprint.id, UUID)
        assert sprint.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_sprint_default_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that default values are set correctly."""
        sprint = KSprint(
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.org_id == test_org_id
        assert sprint.title is None
        assert sprint.status == SprintStatus.BACKLOG
        assert sprint.end_ts is None
        assert sprint.meta == {}
        assert sprint.deleted_at is None
        assert isinstance(sprint.created, datetime)
        assert isinstance(sprint.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_sprint_with_title(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a sprint with a title."""
        sprint = KSprint(
            org_id=test_org_id,
            title="Sprint 1 - Q1 2024",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.title == "Sprint 1 - Q1 2024"

    @pytest.mark.asyncio
    async def test_sprint_with_status(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a sprint with different statuses."""
        sprint = KSprint(
            org_id=test_org_id,
            status=SprintStatus.ACTIVE,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.status == SprintStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_sprint_with_end_ts(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a sprint with an end timestamp."""
        end_time = datetime(2024, 3, 31, 23, 59, 59)
        sprint = KSprint(
            org_id=test_org_id,
            end_ts=end_time,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.end_ts == end_time

    @pytest.mark.asyncio
    async def test_sprint_with_meta_data(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a sprint with metadata."""
        meta_data = {
            "goal": "Complete user authentication",
            "velocity": 42,
            "start_date": "2024-01-01",
        }

        sprint = KSprint(
            org_id=test_org_id,
            title="Sprint 1",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.meta == meta_data

    @pytest.mark.asyncio
    async def test_sprint_audit_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("33333333-3333-3333-3333-333333333333")

        sprint = KSprint(
            org_id=test_org_id,
            title="Sprint 1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)

        assert sprint.created_by == creator_id
        assert sprint.last_modified_by == creator_id

        # Update the sprint
        sprint.title = "Sprint 1 Updated"
        sprint.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(sprint)

        assert sprint.created_by == creator_id  # Should not change
        assert sprint.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_query_sprints_by_org_id(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying sprints by organization ID."""
        from app.models import KOrganization

        # Create a second organization
        other_org = KOrganization(
            id=get_test_org_id(),
            name="Other Organization",
            alias="other_org",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(other_org)
        await session.commit()
        await session.refresh(other_org)

        # Create sprints in different organizations
        sprint1 = KSprint(
            org_id=test_org_id,
            title="Sprint Alpha",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        sprint2 = KSprint(
            org_id=test_org_id,
            title="Sprint Beta",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        sprint3 = KSprint(
            org_id=other_org.id,
            title="Sprint Gamma",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add_all([sprint1, sprint2, sprint3])
        await session.commit()

        # Query sprints for test_org_id
        stmt = select(KSprint).where(
            KSprint.org_id == test_org_id,  # type: ignore[arg-type]
            KSprint.deleted_at.is_(None),  # type: ignore[comparison-overlap]  # noqa: E712
        )
        result = await session.execute(stmt)
        sprints = result.scalars().all()

        assert len(sprints) == 2
        assert all(s.org_id == test_org_id for s in sprints)

    @pytest.mark.asyncio
    async def test_sprint_all_status_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that all sprint status values can be used."""
        statuses = [SprintStatus.BACKLOG, SprintStatus.ACTIVE, SprintStatus.DONE]

        for status in statuses:
            sprint = KSprint(
                org_id=test_org_id,
                title=f"Sprint {status.value}",
                status=status,
                created_by=creator_id,
                last_modified_by=creator_id,
            )
            session.add(sprint)

        await session.commit()

        # Verify all sprints were created
        stmt = select(KSprint).where(
            KSprint.org_id == test_org_id,  # type: ignore[arg-type]
            KSprint.deleted_at.is_(None),  # type: ignore[comparison-overlap]  # noqa: E712
        )
        result = await session.execute(stmt)
        sprints = result.scalars().all()

        assert len(sprints) == 3
        sprint_statuses = {s.status for s in sprints}
        assert sprint_statuses == set(statuses)
