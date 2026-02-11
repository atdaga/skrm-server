"""Unit tests for KSprintTask model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KSprint, KSprintTask, KTask, KTeam
from tests.conftest import get_test_task_id


class TestKSprintTaskModel:
    """Test suite for KSprintTask model."""

    @pytest.fixture
    async def team(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KTeam:
        """Create a test team."""
        team = KTeam(
            name="Test Team",
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(team)
        await session.commit()
        await session.refresh(team)
        return team

    @pytest.fixture
    async def sprint(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ) -> KSprint:
        """Create a test sprint."""
        sprint = KSprint(
            org_id=test_org_id,
            title="Test Sprint",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(sprint)
        await session.commit()
        await session.refresh(sprint)
        return sprint

    @pytest.fixture
    async def task(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ) -> KTask:
        """Create a test task."""
        task = KTask(
            id=get_test_task_id(test_org_id),
            summary="Test Task",
            org_id=test_org_id,
            team_id=team.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    @pytest.mark.asyncio
    async def test_create_sprint_task_with_required_fields(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a sprint task with only required fields."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()
        await session.refresh(sprint_task)

        assert sprint_task.sprint_id == sprint.id
        assert sprint_task.task_id == task.id
        assert sprint_task.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_sprint_task_default_values(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()
        await session.refresh(sprint_task)

        assert sprint_task.role is None
        assert sprint_task.meta == {}
        assert isinstance(sprint_task.created, datetime)
        assert isinstance(sprint_task.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_sprint_task_with_role(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a sprint task with a role."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="primary",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()
        await session.refresh(sprint_task)

        assert sprint_task.role == "primary"

    @pytest.mark.asyncio
    async def test_sprint_task_with_meta_data(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a sprint task with metadata."""
        meta_data = {
            "priority": "high",
            "estimated_hours": 8,
            "dependencies": ["task-123"],
        }

        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="critical",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()
        await session.refresh(sprint_task)

        assert sprint_task.meta == meta_data

    @pytest.mark.asyncio
    async def test_sprint_task_composite_primary_key(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that sprint_id and task_id form a composite primary key."""
        sprint_task1 = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(sprint_task1)

        # Try to create another sprint_task with the same sprint_id and task_id
        sprint_task2 = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_sprint_task_audit_fields(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            role="lead",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()
        await session.refresh(sprint_task)

        assert sprint_task.created_by == creator_id
        assert sprint_task.last_modified_by == creator_id

        # Update the sprint task
        sprint_task.role = "secondary"
        sprint_task.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(sprint_task)

        assert sprint_task.created_by == creator_id  # Should not change
        assert sprint_task.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_sprint_task_cascade_delete_from_sprint(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a sprint cascades to sprint tasks but not the task."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()

        # Delete the sprint
        await session.delete(sprint)
        await session.commit()

        # Verify sprint task is deleted
        result_exec = await session.execute(
            select(KSprintTask).where(KSprintTask.sprint_id == sprint.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify task still exists
        await session.refresh(task)
        assert task.id == task.id

    @pytest.mark.asyncio
    async def test_sprint_task_cascade_delete_from_task(
        self,
        session: AsyncSession,
        sprint: KSprint,
        task: KTask,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a task cascades to sprint tasks but not the sprint."""
        sprint_task = KSprintTask(
            sprint_id=sprint.id,
            task_id=task.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(sprint_task)
        await session.commit()

        # Delete the task
        await session.delete(task)
        await session.commit()

        # Verify sprint task is deleted
        result_exec = await session.execute(
            select(KSprintTask).where(KSprintTask.task_id == task.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify sprint still exists
        await session.refresh(sprint)
        assert sprint.id == sprint.id
