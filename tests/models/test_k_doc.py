"""Unit tests for KDoc model."""

from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.k_doc import KDoc


class TestKDocModel:
    """Test suite for KDoc model."""

    @pytest.mark.asyncio
    async def test_create_doc_with_required_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a doc with only required fields."""
        doc = KDoc(
            org_id=test_org_id,
            name="API Documentation",
            content="This is the API documentation content.",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.id is not None
        assert isinstance(doc.id, UUID)
        assert doc.name == "API Documentation"
        assert doc.content == "This is the API documentation content."

    @pytest.mark.asyncio
    async def test_doc_default_values(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that default values are set correctly."""
        doc = KDoc(
            org_id=test_org_id,
            name="User Guide",
            content="User guide content here.",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.org_id == test_org_id
        assert doc.description is None
        assert doc.meta == {}
        assert isinstance(doc.created, datetime)
        assert isinstance(doc.last_modified, datetime)

    @pytest.mark.asyncio
    async def test_doc_with_all_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a doc with all fields populated."""
        meta_data = {
            "version": "1.0",
            "tags": ["api", "rest"],
            "language": "en",
        }

        doc = KDoc(
            org_id=test_org_id,
            name="REST API Guide",
            description="Comprehensive guide for REST API",
            content="# REST API Guide\n\n## Introduction\n\nThis guide covers...",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.description == "Comprehensive guide for REST API"
        assert "# REST API Guide" in doc.content
        assert doc.meta == meta_data

    @pytest.mark.asyncio
    async def test_doc_with_large_content(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a doc with large content (Text field)."""
        large_content = "Lorem ipsum dolor sit amet. " * 1000  # Large text content

        doc = KDoc(
            org_id=test_org_id,
            name="Large Document",
            content=large_content,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert len(doc.content) == len(large_content)
        assert doc.content == large_content

    @pytest.mark.asyncio
    async def test_doc_unique_name_per_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that doc names must be unique per organization."""
        doc1 = KDoc(
            org_id=test_org_id,
            name="Duplicate Doc",
            content="First doc content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc1)
        await session.commit()

        # Try to create another doc with the same name in the same org
        doc2 = KDoc(
            org_id=test_org_id,
            name="Duplicate Doc",
            content="Second doc content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc2)
        with pytest.raises(IntegrityError):
            await session.commit()

    @pytest.mark.asyncio
    async def test_doc_same_name_different_org(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that doc names can be the same across different organizations."""
        other_org_id = UUID("22222222-2222-2222-2222-222222222222")

        doc1 = KDoc(
            org_id=test_org_id,
            name="Installation Guide",
            content="Installation guide for org 1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        doc2 = KDoc(
            org_id=other_org_id,
            name="Installation Guide",
            content="Installation guide for org 2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc1)
        session.add(doc2)
        await session.commit()
        await session.refresh(doc1)
        await session.refresh(doc2)

        assert doc1.name == doc2.name
        assert doc1.org_id != doc2.org_id
        assert doc1.content != doc2.content

    @pytest.mark.asyncio
    async def test_doc_with_markdown_content(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a doc with markdown formatted content."""
        markdown_content = """# Getting Started

## Prerequisites

- Python 3.9+
- PostgreSQL 13+

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Edit the `.env` file with your settings.

## Usage

Run the application:

```bash
python main.py
```
"""

        doc = KDoc(
            org_id=test_org_id,
            name="Getting Started",
            description="Quick start guide",
            content=markdown_content,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert "# Getting Started" in doc.content
        assert "## Prerequisites" in doc.content
        assert "```bash" in doc.content

    @pytest.mark.asyncio
    async def test_doc_audit_fields(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test that audit fields are properly set."""
        modifier_id = UUID("33333333-3333-3333-3333-333333333333")

        doc = KDoc(
            org_id=test_org_id,
            name="Audited Doc",
            content="Original content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.created_by == creator_id
        assert doc.last_modified_by == creator_id

        # Update the doc
        doc.content = "Updated content"
        doc.last_modified_by = modifier_id
        await session.commit()
        await session.refresh(doc)

        assert doc.created_by == creator_id  # Should not change
        assert doc.last_modified_by == modifier_id
        assert doc.content == "Updated content"

    @pytest.mark.asyncio
    async def test_query_docs_by_org_id(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test querying docs by organization ID."""
        other_org_id = UUID("44444444-4444-4444-4444-444444444444")

        # Create docs in different organizations
        doc1 = KDoc(
            org_id=test_org_id,
            name="Doc 1",
            content="Content 1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        doc2 = KDoc(
            org_id=test_org_id,
            name="Doc 2",
            content="Content 2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        doc3 = KDoc(
            org_id=other_org_id,
            name="Doc 3",
            content="Content 3",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add_all([doc1, doc2, doc3])
        await session.commit()

        # Query docs for test_org_id
        stmt = select(KDoc).where(KDoc.org_id == test_org_id)  # type: ignore[arg-type]
        result = await session.execute(stmt)
        docs = result.scalars().all()

        assert len(docs) == 2
        assert all(d.org_id == test_org_id for d in docs)

    @pytest.mark.asyncio
    async def test_doc_with_empty_content(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test creating a doc with empty content string."""
        doc = KDoc(
            org_id=test_org_id,
            name="Empty Doc",
            content="",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.content == ""
        assert doc.name == "Empty Doc"

    @pytest.mark.asyncio
    async def test_doc_description_max_length(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test doc description field with max length constraint."""
        description = "A" * 255  # Max length

        doc = KDoc(
            org_id=test_org_id,
            name="Test Doc",
            description=description,
            content="Test content",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert len(doc.description) == 255
        assert doc.description == description

    @pytest.mark.asyncio
    async def test_doc_with_json_metadata(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test doc with complex JSON metadata."""
        complex_meta = {
            "version": "2.1.0",
            "tags": ["api", "rest", "authentication"],
            "authors": [
                {"name": "John Doe", "role": "writer"},
                {"name": "Jane Smith", "role": "reviewer"},
            ],
            "changelog": {
                "2.1.0": "Added authentication section",
                "2.0.0": "Major rewrite",
                "1.0.0": "Initial version",
            },
            "settings": {
                "public": True,
                "comments_enabled": False,
                "version_control": True,
            },
        }

        doc = KDoc(
            org_id=test_org_id,
            name="Complex Doc",
            content="Content with complex metadata",
            meta=complex_meta,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.meta == complex_meta
        assert doc.meta["version"] == "2.1.0"
        assert len(doc.meta["tags"]) == 3
        assert doc.meta["authors"][0]["name"] == "John Doe"
        assert doc.meta["settings"]["public"] is True

    @pytest.mark.asyncio
    async def test_update_doc_content(
        self, session: AsyncSession, creator_id: UUID, test_org_id: UUID
    ):
        """Test updating doc content over time."""
        doc = KDoc(
            org_id=test_org_id,
            name="Evolving Doc",
            content="Version 1 content",
            description="Version 1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        original_created = doc.created
        original_id = doc.id

        # Update content
        doc.content = "Version 2 content"
        doc.description = "Version 2"
        await session.commit()
        await session.refresh(doc)

        assert doc.id == original_id  # ID should not change
        assert doc.created == original_created  # Created timestamp should not change
        assert doc.content == "Version 2 content"
        assert doc.description == "Version 2"
