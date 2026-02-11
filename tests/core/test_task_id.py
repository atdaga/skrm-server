"""Unit tests for task ID generation utilities."""

from uuid import UUID

import pytest

from app.core.task_id import (
    MAX_TASK_NUMBER,
    extract_task_number,
    generate_task_id,
)


class TestGenerateTaskId:
    """Tests for generate_task_id function."""

    def test_basic_generation(self) -> None:
        """Test basic task ID generation with simple inputs."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        task_id = generate_task_id(org_id, 1)
        assert task_id == UUID("00000010-0000-0000-0001-000000000001")

    def test_second_task(self) -> None:
        """Test generating the second task ID."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        task_id = generate_task_id(org_id, 2)
        assert task_id == UUID("00000010-0000-0000-0001-000000000002")

    def test_large_task_number(self) -> None:
        """Test generating task ID with a large task number."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        task_id = generate_task_id(org_id, 123456789012)
        assert task_id == UUID("00000010-0000-0000-0001-123456789012")

    def test_max_task_number(self) -> None:
        """Test generating task ID with the maximum task number."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        task_id = generate_task_id(org_id, MAX_TASK_NUMBER)
        assert task_id == UUID("00000010-0000-0000-0001-999999999999")

    def test_different_org_id(self) -> None:
        """Test that different org IDs produce different task IDs."""
        org_id_1 = UUID("11111111-2222-3333-4444-555555555555")
        org_id_2 = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        task_id_1 = generate_task_id(org_id_1, 1)
        task_id_2 = generate_task_id(org_id_2, 1)

        assert task_id_1 == UUID("11111111-2222-3333-4444-000000000001")
        assert task_id_2 == UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001")
        assert task_id_1 != task_id_2

    def test_invalid_task_number_zero(self) -> None:
        """Test that task number 0 raises ValueError."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        with pytest.raises(ValueError, match="Task number must be between 1 and"):
            generate_task_id(org_id, 0)

    def test_invalid_task_number_negative(self) -> None:
        """Test that negative task numbers raise ValueError."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        with pytest.raises(ValueError, match="Task number must be between 1 and"):
            generate_task_id(org_id, -1)

    def test_invalid_task_number_too_large(self) -> None:
        """Test that task numbers exceeding max raise ValueError."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        with pytest.raises(ValueError, match="Task number must be between 1 and"):
            generate_task_id(org_id, MAX_TASK_NUMBER + 1)


class TestExtractTaskNumber:
    """Tests for extract_task_number function."""

    def test_basic_extraction(self) -> None:
        """Test basic task number extraction."""
        task_id = UUID("00000010-0000-0000-0001-000000000001")
        assert extract_task_number(task_id) == 1

    def test_extraction_with_padding(self) -> None:
        """Test extraction handles leading zeros correctly."""
        task_id = UUID("00000010-0000-0000-0001-000000000123")
        assert extract_task_number(task_id) == 123

    def test_large_number_extraction(self) -> None:
        """Test extraction of large task numbers."""
        task_id = UUID("00000010-0000-0000-0001-123456789012")
        assert extract_task_number(task_id) == 123456789012

    def test_max_number_extraction(self) -> None:
        """Test extraction of maximum task number."""
        task_id = UUID("00000010-0000-0000-0001-999999999999")
        assert extract_task_number(task_id) == 999999999999

    def test_roundtrip(self) -> None:
        """Test that generate and extract are inverse operations."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        for task_number in [1, 42, 1000, 999999999999]:
            task_id = generate_task_id(org_id, task_number)
            extracted = extract_task_number(task_id)
            assert extracted == task_number
