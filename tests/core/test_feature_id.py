"""Unit tests for feature ID generation utilities."""

from uuid import UUID

import pytest

from app.core.feature_id import (
    MAX_FEATURE_NUMBER,
    extract_feature_number,
    generate_feature_id,
)


class TestGenerateFeatureId:
    """Tests for generate_feature_id function."""

    def test_basic_generation(self) -> None:
        """Test basic feature ID generation with simple inputs."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        feature_id = generate_feature_id(org_id, 1)
        assert feature_id == UUID("00000010-0000-0000-0001-000000000001")

    def test_second_feature(self) -> None:
        """Test generating the second feature ID."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        feature_id = generate_feature_id(org_id, 2)
        assert feature_id == UUID("00000010-0000-0000-0001-000000000002")

    def test_large_feature_number(self) -> None:
        """Test generating feature ID with a large feature number."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        feature_id = generate_feature_id(org_id, 123456789012)
        assert feature_id == UUID("00000010-0000-0000-0001-123456789012")

    def test_max_feature_number(self) -> None:
        """Test generating feature ID with the maximum feature number."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        feature_id = generate_feature_id(org_id, MAX_FEATURE_NUMBER)
        assert feature_id == UUID("00000010-0000-0000-0001-999999999999")

    def test_different_org_id(self) -> None:
        """Test that different org IDs produce different feature IDs."""
        org_id_1 = UUID("11111111-2222-3333-4444-555555555555")
        org_id_2 = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        feature_id_1 = generate_feature_id(org_id_1, 1)
        feature_id_2 = generate_feature_id(org_id_2, 1)

        assert feature_id_1 == UUID("11111111-2222-3333-4444-000000000001")
        assert feature_id_2 == UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001")
        assert feature_id_1 != feature_id_2

    def test_invalid_feature_number_zero(self) -> None:
        """Test that feature number 0 raises ValueError."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        with pytest.raises(ValueError, match="Feature number must be between 1 and"):
            generate_feature_id(org_id, 0)

    def test_invalid_feature_number_negative(self) -> None:
        """Test that negative feature numbers raise ValueError."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        with pytest.raises(ValueError, match="Feature number must be between 1 and"):
            generate_feature_id(org_id, -1)

    def test_invalid_feature_number_too_large(self) -> None:
        """Test that feature numbers exceeding max raise ValueError."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        with pytest.raises(ValueError, match="Feature number must be between 1 and"):
            generate_feature_id(org_id, MAX_FEATURE_NUMBER + 1)


class TestExtractFeatureNumber:
    """Tests for extract_feature_number function."""

    def test_basic_extraction(self) -> None:
        """Test basic feature number extraction."""
        feature_id = UUID("00000010-0000-0000-0001-000000000001")
        assert extract_feature_number(feature_id) == 1

    def test_extraction_with_padding(self) -> None:
        """Test extraction handles leading zeros correctly."""
        feature_id = UUID("00000010-0000-0000-0001-000000000123")
        assert extract_feature_number(feature_id) == 123

    def test_large_number_extraction(self) -> None:
        """Test extraction of large feature numbers."""
        feature_id = UUID("00000010-0000-0000-0001-123456789012")
        assert extract_feature_number(feature_id) == 123456789012

    def test_max_number_extraction(self) -> None:
        """Test extraction of maximum feature number."""
        feature_id = UUID("00000010-0000-0000-0001-999999999999")
        assert extract_feature_number(feature_id) == 999999999999

    def test_roundtrip(self) -> None:
        """Test that generate and extract are inverse operations."""
        org_id = UUID("00000010-0000-0000-0001-000000000010")
        for feature_number in [1, 42, 1000, 999999999999]:
            feature_id = generate_feature_id(org_id, feature_number)
            extracted = extract_feature_number(feature_id)
            assert extracted == feature_number
