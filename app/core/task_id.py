"""Task ID generation utilities.

Task IDs use a custom format that combines the organization ID prefix
with an incrementing task number:
- First 4 sections: From the organization ID
- Last section: Incrementing number (base 10, padded to 12 digits)

Example:
    For org `00000010-0000-0000-0001-000000000010`:
    - Task 1: `00000010-0000-0000-0001-000000000001`
    - Task 2: `00000010-0000-0000-0001-000000000002`
"""

from uuid import UUID

MAX_TASK_NUMBER = 999_999_999_999  # 12 digits


def generate_task_id(org_id: UUID, task_number: int) -> UUID:
    """Generate task ID: {org_sections_1-4}-{task_number_padded_12}.

    Args:
        org_id: The organization's UUID
        task_number: The incrementing task number (1 to 999_999_999_999)

    Returns:
        A UUID combining the org prefix with the padded task number

    Raises:
        ValueError: If task_number is outside the valid range
    """
    if task_number < 1 or task_number > MAX_TASK_NUMBER:
        raise ValueError(f"Task number must be between 1 and {MAX_TASK_NUMBER}")

    org_prefix = "-".join(str(org_id).split("-")[:4])
    task_suffix = str(task_number).zfill(12)
    return UUID(f"{org_prefix}-{task_suffix}")


def extract_task_number(task_id: UUID) -> int:
    """Extract the task number from a task ID.

    Args:
        task_id: The task's UUID

    Returns:
        The task number extracted from the last section of the UUID
    """
    return int(str(task_id).split("-")[4])


__all__ = ["generate_task_id", "extract_task_number", "MAX_TASK_NUMBER"]
