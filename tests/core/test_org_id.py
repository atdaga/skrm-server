"""Unit tests for organization ID generation utilities."""

from uuid import UUID

from app.core.org_id import extract_org_prefix, generate_org_id


class TestGenerateOrgId:
    """Tests for generate_org_id function."""

    def test_returns_uuid(self) -> None:
        """Test that generate_org_id returns a UUID."""
        org_id = generate_org_id()
        assert isinstance(org_id, UUID)

    def test_generates_unique_ids(self) -> None:
        """Test that multiple calls generate different IDs."""
        ids = [generate_org_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_generates_valid_uuid_format(self) -> None:
        """Test that generated IDs are valid UUID format."""
        org_id = generate_org_id()
        # Should be able to convert to string and back
        org_id_str = str(org_id)
        assert UUID(org_id_str) == org_id
        # Should have 5 sections separated by hyphens
        parts = org_id_str.split("-")
        assert len(parts) == 5


class TestExtractOrgPrefix:
    """Tests for extract_org_prefix function."""

    def test_basic_extraction(self) -> None:
        """Test basic prefix extraction."""
        org_id = UUID("11111111-2222-3333-4444-555555555555")
        prefix = extract_org_prefix(org_id)
        assert prefix == "11111111-2222-3333-4444"

    def test_extraction_with_different_values(self) -> None:
        """Test extraction with various UUID values."""
        test_cases = [
            (UUID("00000010-0000-0000-0001-000000000010"), "00000010-0000-0000-0001"),
            (UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"), "aaaaaaaa-bbbb-cccc-dddd"),
            (UUID("12345678-1234-5678-1234-567812345678"), "12345678-1234-5678-1234"),
        ]
        for org_id, expected_prefix in test_cases:
            assert extract_org_prefix(org_id) == expected_prefix

    def test_prefix_uniqueness_implies_different_orgs(self) -> None:
        """Test that different prefixes imply different org ID spaces."""
        org1 = UUID("11111111-1111-1111-1111-111111111111")
        org2 = UUID("22222222-2222-2222-2222-222222222222")

        prefix1 = extract_org_prefix(org1)
        prefix2 = extract_org_prefix(org2)

        assert prefix1 != prefix2

    def test_same_prefix_different_suffix(self) -> None:
        """Test that same prefix with different suffix extracts same prefix."""
        org1 = UUID("11111111-2222-3333-4444-000000000001")
        org2 = UUID("11111111-2222-3333-4444-999999999999")

        prefix1 = extract_org_prefix(org1)
        prefix2 = extract_org_prefix(org2)

        assert prefix1 == prefix2 == "11111111-2222-3333-4444"

    def test_roundtrip_with_generate(self) -> None:
        """Test that generated IDs can have their prefix extracted."""
        for _ in range(10):
            org_id = generate_org_id()
            prefix = extract_org_prefix(org_id)
            # Prefix should be 4 sections
            parts = prefix.split("-")
            assert len(parts) == 4
            # Each part should be valid hex
            for part in parts:
                int(part, 16)  # Should not raise
