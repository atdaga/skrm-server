"""Unit tests for sprint business logic."""


import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import SprintUpdateConflictException
from app.logic.v1.sprints import create_sprint
from app.schemas.sprint import SprintCreate


class TestCreateSprint:
    """Test suite for create_sprint logic function."""

    @pytest.mark.asyncio
    async def test_create_sprint_integrity_error(
        self,
        async_session: AsyncSession,
        test_user_id,
        test_organization,
        mocker,
    ):
        """Test creating a sprint that causes an IntegrityError."""
        # Arrange
        # Store org_id before mocking to avoid lazy loading issues
        org_id = test_organization.id

        sprint_data = SprintCreate(
            title="Test Sprint",
            status="Active",
            meta={"test": "data"},
        )

        # Mock db.commit to raise IntegrityError
        mocker.patch.object(
            async_session,
            "commit",
            side_effect=IntegrityError(
                statement="INSERT INTO k_sprint",
                params={},
                orig=Exception("Foreign key constraint violation"),
            ),
        )

        # Act & Assert
        with pytest.raises(SprintUpdateConflictException) as exc_info:
            await create_sprint(
                sprint_data=sprint_data,
                user_id=test_user_id,
                org_id=org_id,
                db=async_session,
            )

        # Verify the exception contains the org_id
        assert str(org_id) in exc_info.value.message
