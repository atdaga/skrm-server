"""Unit tests for KProject model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_project import KProject


class TestKProjectModel:
    """Test suite for KProject model."""

    @pytest.mark.asyncio
    async def test_create_project_with_required_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a project with only required fields."""
        project = KProject(
            org_id=test_org_id,
            name="Mobile App",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        assert project.id is not None
        assert isinstance(project.id, UUID)
        assert project.name == "Mobile App"

    @pytest.mark.asyncio
    async def test_project_default_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that default values are set correctly."""
        project = KProject(
            org_id=test_org_id,
            name="Backend API",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        assert project.org_id == test_org_id
        assert project.description is None
        assert project.meta == {}
        assert isinstance(project.created, datetime)
        assert isinstance(project.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_project_with_description(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a project with a description."""
        project = KProject(
            org_id=test_org_id,
            name="Frontend Redesign",
            description="Complete UI overhaul for 2024",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        assert project.description == "Complete UI overhaul for 2024"

    @pytest.mark.asyncio
    async def test_project_with_meta_data(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a project with metadata."""
        meta_data = {
            "priority": "high",
            "budget": 500000,
            "start_date": "2024-01-01",
        }

        project = KProject(
            org_id=test_org_id,
            name="Platform Migration",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        assert project.meta == meta_data

    @pytest.mark.asyncio
    async def test_project_unique_name_per_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that project names must be unique per organization."""
        project1 = KProject(
            org_id=test_org_id,
            name="Infrastructure",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project1)
        await session.commit()

        # Try to create another project with the same name in the same org
        project2 = KProject(
            org_id=test_org_id,
            name="Infrastructure",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_project_same_name_different_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that project names can be the same across different organizations."""
        from app.models import KOrganization

        # Create a second organization
        other_org = KOrganization(
            name="Other Organization",
            alias="other_org",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(other_org)
        await session.commit()
        await session.refresh(other_org)

        project1 = KProject(
            org_id=test_org_id,
            name="DevOps",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        project2 = KProject(
            org_id=other_org.id,
            name="DevOps",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project1)
        session.add(project2)
        await session.commit()
        await session.refresh(project1)
        await session.refresh(project2)

        assert project1.name == project2.name
        assert project1.org_id != project2.org_id

    @pytest.mark.asyncio
    async def test_project_audit_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("33333333-3333-3333-3333-333333333333")

        project = KProject(
            org_id=test_org_id,
            name="Security Audit",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)

        assert project.created_by == creator_id
        assert project.last_modified_by == creator_id

        # Update the project
        project.name = "Security Audit Updated"
        project.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(project)

        assert project.created_by == creator_id  # Should not change
        assert project.last_modified_by == modifier_id

    @pytest.mark.asyncio
    async def test_query_projects_by_org_id(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying projects by organization ID."""
        from app.models import KOrganization

        # Create a second organization
        other_org = KOrganization(
            name="Other Organization",
            alias="other_org_query",
            created_by=creator_id,
            last_modified_by=creator_id,
        )
        session.add(other_org)
        await session.commit()
        await session.refresh(other_org)

        # Create projects in different organizations
        project1 = KProject(
            org_id=test_org_id,
            name="Project Alpha",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        project2 = KProject(
            org_id=test_org_id,
            name="Project Beta",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        project3 = KProject(
            org_id=other_org.id,
            name="Project Gamma",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add_all([project1, project2, project3])
        await session.commit()

        # Query projects for test_org_id
        stmt = select(KProject).where(
            KProject.org_id == test_org_id,  # type: ignore[arg-type]
            KProject.deleted_at.is_(None),  # type: ignore[comparison-overlap]  # noqa: E712
        )
        result = await session.execute(stmt)
        projects = result.scalars().all()

        assert len(projects) == 2
        assert all(p.org_id == test_org_id for p in projects)
