"""Unit tests for KTaskOwner model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import KPrincipal, KTask, KTaskOwner, KTeam


class TestKTaskOwnerModel:
    """Test suite for KTaskOwner model."""

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
            username="testowner",
            primary_email="testowner@example.com",
            first_name="Test",
            last_name="Owner",
            display_name="Test Owner",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(principal)
        await session.commit()
        await session.refresh(principal)
        return principal

    @pytest.mark.asyncio
    async def test_create_task_owner_with_required_fields(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task owner with only required fields."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()
        await session.refresh(task_owner)

        assert task_owner.task_id == task.id
        assert task_owner.principal_id == principal.id
        assert task_owner.org_id == test_org_id

    @pytest.mark.asyncio
    async def test_task_owner_default_values(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that default values are set correctly."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()
        await session.refresh(task_owner)

        assert task_owner.role is None
        assert task_owner.meta == {}
        assert isinstance(task_owner.created, datetime)
        assert isinstance(task_owner.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_task_owner_with_role(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task owner with a role."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()
        await session.refresh(task_owner)

        assert task_owner.role == "lead"

    @pytest.mark.asyncio
    async def test_task_owner_with_meta_data(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test creating a task owner with metadata."""
        meta_data = {
            "responsibility": "implementation",
            "allocation": 100,
        }

        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="primary",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()
        await session.refresh(task_owner)

        assert task_owner.meta == meta_data

    @pytest.mark.asyncio
    async def test_task_owner_composite_primary_key(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that task_id and principal_id form a composite primary key."""
        task_owner1 = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner1)
        await session.commit()

        # Clear session to test database constraint (not session constraint)
        session.expunge(task_owner1)

        # Try to create another task_owner with the same task_id and principal_id
        task_owner2 = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="different role",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_task_owner_audit_fields(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("55555555-5555-5555-5555-555555555555")

        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            role="lead",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()
        await session.refresh(task_owner)

        assert task_owner.created_by == creator_id
        assert task_owner.last_modified_by == creator_id

        # Update the task owner
        task_owner.role = "secondary"
        task_owner.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(task_owner)

        assert task_owner.created_by == creator_id  # Should not change
        assert task_owner.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_task_owner_cascade_delete_from_task(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a task cascades to task owners but not the principal."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()

        # Delete the task
        await session.delete(task)
        await session.commit()

        # Verify task owner is deleted
        result_exec = await session.execute(
            select(KTaskOwner).where(KTaskOwner.task_id == task.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify principal still exists
        await session.refresh(principal)
        assert principal.id == principal.id

    @pytest.mark.asyncio
    async def test_task_owner_cascade_delete_from_principal(
        self,
        session: AsyncSession,
        task: KTask,
        principal: KPrincipal,
        creator_id: UUID,
        test_org_id: UUID,
    ):
        """Test that deleting a principal cascades to task owners but not the task."""
        task_owner = KTaskOwner(
            task_id=task.id,
            principal_id=principal.id,
            org_id=test_org_id,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(task_owner)
        await session.commit()

        # Delete the principal
        await session.delete(principal)
        await session.commit()

        # Verify task owner is deleted
        result_exec = await session.execute(
            select(KTaskOwner).where(KTaskOwner.principal_id == principal.id)
        )
        result = result_exec.scalar_one_or_none()
        assert result is None

        # Verify task still exists
        await session.refresh(task)
        assert task.id == task.id
