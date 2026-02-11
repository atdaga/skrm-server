"""Organization ID generation utilities.

Organization IDs use a format where the first 4 sections form a unique prefix.
This prefix is used as the basis for generating task and feature IDs within
the organization.

Format: {unique_prefix_4_sections}-{random_suffix_12}
Example: 11111111-2222-3333-4444-555555555555
         ^^^^^^^^^^^^^^^^^^^^^^^^^^ unique prefix
"""

from uuid import UUID, uuid4


def generate_org_id() -> UUID:
    """Generate a new organization ID.

    The ID is a standard UUID4, but the first 4 sections should be
    checked for uniqueness against existing organizations before use.

    Returns:
        A new UUID for organization identification
    """
    return uuid4()


def extract_org_prefix(org_id: UUID) -> str:
    """Extract the first 4 sections of an organization ID.

    This prefix is used to ensure uniqueness across organizations
    and forms the basis for task/feature ID generation.

    Args:
        org_id: Organization UUID

    Returns:
        The first 4 sections of the UUID as a string (e.g., "11111111-2222-3333-4444")
    """
    parts = str(org_id).split("-")
    return "-".join(parts[:4])


__all__ = ["extract_org_prefix", "generate_org_id"]
