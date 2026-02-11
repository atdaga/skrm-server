"""add_task_feature_links_for_active_sprint

Revision ID: 4a8b2c3d5e6f
Revises: e3859e843f7f
Create Date: 2026-02-10 18:13:30.000000

Links 14 tasks in the active sprint to features.
These tasks were added in the extended mock data migration but weren't given feature associations.

Only runs when SEED_MOCK_DATA=true environment variable is set.

Usage:
    SEED_MOCK_DATA=true uv run alembic upgrade head
"""

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a8b2c3d5e6f"
down_revision: str | Sequence[str] | None = "e3859e843f7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# =============================================================================
# CONSTANTS
# =============================================================================

UUIDS = {
    # Organization
    "org_acme": "00000010-0000-0000-0001-000000000010",
    # Features
    "feature_user_mgmt": "00000010-0000-0000-0001-000000000001",
    "feature_user_profiles": "00000010-0000-0000-0001-000000000003",
    "feature_dashboard": "00000010-0000-0000-0001-000000000004",
    "feature_api_gateway": "00000010-0000-0000-0001-000000000007",
    "feature_user_mgmt_core": "00000010-0000-0000-0001-000000000012",
    # Tasks
    "task_19": "00000010-0000-0000-0001-000000000019",
    "task_20": "00000010-0000-0000-0001-000000000020",
    "task_21": "00000010-0000-0000-0001-000000000021",
    "task_22": "00000010-0000-0000-0001-000000000022",
    "task_23": "00000010-0000-0000-0001-000000000023",
    "task_24": "00000010-0000-0000-0001-000000000024",
    "task_25": "00000010-0000-0000-0001-000000000025",
    "task_26": "00000010-0000-0000-0001-000000000026",
    "task_27": "00000010-0000-0000-0001-000000000027",
    "task_29": "00000010-0000-0000-0001-000000000029",
    "task_30": "00000010-0000-0000-0001-000000000030",
    "task_31": "00000010-0000-0000-0001-000000000031",
    "task_32": "00000010-0000-0000-0001-000000000032",
    "task_33": "00000010-0000-0000-0001-000000000033",
}

# Root user UUID (for created_by / last_modified_by)
ROOT_USER = "00000000-0000-0000-0000-000000000000"

# Timestamp for all records
TIMESTAMP = "2025-01-15 10:00:00.000000"

# Task to Feature mappings
# (task_key, feature_key)
TASK_FEATURE_LINKS = [
    # API Gateway related tasks
    ("task_19", "feature_api_gateway"),  # Add API documentation generator
    ("task_21", "feature_api_gateway"),  # Create performance benchmarks
    ("task_22", "feature_api_gateway"),  # Implement GraphQL endpoint
    ("task_23", "feature_api_gateway"),  # Build log aggregation service
    ("task_24", "feature_api_gateway"),  # Create integration test suite
    ("task_27", "feature_api_gateway"),  # Create security scanning pipeline
    ("task_29", "feature_api_gateway"),  # Deploy CDN configuration
    ("task_30", "feature_api_gateway"),  # Deploy QA test environment
    ("task_33", "feature_api_gateway"),  # Review load testing scripts
    # Dashboard related tasks
    ("task_20", "feature_dashboard"),    # Build accessibility checker
    ("task_31", "feature_dashboard"),    # Review form validation library
    # User Management related tasks
    ("task_25", "feature_user_profiles"),     # Add user search functionality
    ("task_26", "feature_user_mgmt_core"),    # Implement audit logging
    ("task_32", "feature_user_mgmt_core"),    # Review database indexing strategy
]


# =============================================================================
# UPGRADE
# =============================================================================


def upgrade() -> None:
    """Upgrade schema - add task-feature links for active sprint tasks."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping task-feature links. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Adding task-feature links for active sprint tasks...")

    _insert_task_feature_links()

    print("Task-feature links added!")


def _insert_task_feature_links() -> None:
    """Insert task-feature relationships."""
    org_id = UUIDS["org_acme"]

    for task_key, feature_key in TASK_FEATURE_LINKS:
        task_uuid = UUIDS[task_key]
        feature_uuid = UUIDS[feature_key]
        op.execute(f"""
            INSERT INTO k_task_feature (
                task_id, feature_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{task_uuid}'::uuid, '{feature_uuid}'::uuid, '{org_id}'::uuid,
                'implements', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


# =============================================================================
# DOWNGRADE
# =============================================================================


def downgrade() -> None:
    """Downgrade schema - remove task-feature links."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping task-feature links removal. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Removing task-feature links for active sprint tasks...")

    _delete_task_feature_links()

    print("Task-feature links removed!")


def _delete_task_feature_links() -> None:
    """Delete task-feature relationships added by this migration."""
    for task_key, _ in TASK_FEATURE_LINKS:
        task_uuid = UUIDS[task_key]
        op.execute(f"DELETE FROM k_task_feature WHERE task_id = '{task_uuid}'::uuid")
