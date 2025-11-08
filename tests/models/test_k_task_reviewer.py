"""Unit tests for KTaskReviewer model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KPrincipal, KTask, KTaskReviewer, KTeam


class TestKTaskReviewerModel:
    """Test suite for KTaskReviewer model."""

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
    async def task(
        self, session: AsyncSession, team: KTeam, creator_id: UUID, test_org_id: UUID
    ) -> KTask:
        """Create a test task."""
        task = KTask(
            name="Test Task",
            org_id=test_org_id,
            team_id=team.id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    @pytest.fixture
    async def principal(self, session: AsyncSession, creator_id: UUID) -> KPrincipal:
        """Create a test principal."""
        principal = KPrincipal(
            username="testreviewer",
            primary_email="testreviewer@example.com",
            first_name="Test",
            last_name="Reviewer",
            display_name="Test Reviewer",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(principal)
        await session.commit()
        await session.refresh(principal)
        return principal

    @pytest.mark.asyncio
    async def test_create_task_reviewer_with_required_fields(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task reviewer with only required fields."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()
        await session.refresh(task_reviewer)

        assert task_reviewer.task_id == task.id
        assert task_reviewer.principal_id == principal.id
        assert task_reviewer.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_task_reviewer_default_values(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()
        await session.refresh(task_reviewer)

        assert task_reviewer.role is None
        assert task_reviewer.meta == {}
        assert isinstance(task_reviewer.created, datetime)
        assert isinstance(task_reviewer.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_task_reviewer_with_role(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task reviewer with a role."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="technical",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()
        await session.refresh(task_reviewer)

        assert task_reviewer.role == "technical"

    @pytest.mark.asyncio
    async def test_task_reviewer_with_meta_data(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task reviewer with metadata."""
        meta_data = {
            "review_type": "code",
            "expertise_area": "security",
        }

        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="security_reviewer",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()
        await session.refresh(task_reviewer)

        assert task_reviewer.meta == meta_data

    @pytest.mark.asyncio
    async def test_task_reviewer_composite_primary_key(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that task_id and principal_id form a composite primary key."""
        task_reviewer1 = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(task_reviewer1)

        # Try to create another task_reviewer with the same task_id and principal_id
        task_reviewer2 = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_task_reviewer_audit_fields(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="technical",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()
        await session.refresh(task_reviewer)

        assert task_reviewer.created_by == creator_id
        assert task_reviewer.last_modified_by == creator_id

        # Update the task reviewer
        task_reviewer.role = "functional"
        task_reviewer.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(task_reviewer)

        assert task_reviewer.created_by == creator_id  # Should not change
        assert task_reviewer.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_task_reviewer_cascade_delete_from_task(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a task cascades to task reviewers but not the principal."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()

        # Delete the task
        await session.delete(task)
        await session.commit()

        # Verify task reviewer is deleted
        result_exec = await session.execute(
            select(KTaskReviewer).where(KTaskReviewer.task_id == task.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify principal still exists
        await session.refresh(principal)
        assert principal.id == principal.id

    @pytest.mark.asyncio
    async def test_task_reviewer_cascade_delete_from_principal(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a principal cascades to task reviewers but not the task."""
        task_reviewer = KTaskReviewer(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_reviewer)
        await session.commit()

        # Delete the principal
        await session.delete(principal)
        await session.commit()

        # Verify task reviewer is deleted
        result_exec = await session.execute(
            select(KTaskReviewer).where(KTaskReviewer.principal_id == principal.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify task still exists
        await session.refresh(task)
        assert task.id == task.id
