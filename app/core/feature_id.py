"""Feature ID generation utilities.

Feature IDs use a custom format that combines the organization ID prefix
with an incrementing feature number:
- First 4 sections: From the organization ID
- Last section: Incrementing number (base 10, padded to 12 digits)

Example:
    For org `00000010-0000-0000-0001-000000000010`:
    - Feature 1: `00000010-0000-0000-0001-000000000001`
    - Feature 2: `00000010-0000-0000-0001-000000000002`
"""

from uuid import UUID

MAX_FEATURE_NUMBER = 999_999_999_999  # 12 digits


def generate_feature_id(org_id: UUID, feature_number: int) -> UUID:
    """Generate feature ID: {org_sections_1-4}-{feature_number_padded_12}.

    Args:
        org_id: The organization's UUID
        feature_number: The incrementing feature number (1 to 999_999_999_999)

    Returns:
        A UUID combining the org prefix with the padded feature number

    Raises:
        ValueError: If feature_number is outside the valid range
    """
    if feature_number < 1 or feature_number > MAX_FEATURE_NUMBER:
        raise ValueError(f"Feature number must be between 1 and {MAX_FEATURE_NUMBER}")

    org_prefix = "-".join(str(org_id).split("-")[:4])
    feature_suffix = str(feature_number).zfill(12)
    return UUID(f"{org_prefix}-{feature_suffix}")


def extract_feature_number(feature_id: UUID) -> int:
    """Extract the feature number from a feature ID.

    Args:
        feature_id: The feature's UUID

    Returns:
        The feature number extracted from the last section of the UUID
    """
    return int(str(feature_id).split("-")[4])


__all__ = ["generate_feature_id", "extract_feature_number", "MAX_FEATURE_NUMBER"]
