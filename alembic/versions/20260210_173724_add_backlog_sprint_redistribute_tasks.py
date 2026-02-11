"""add_backlog_sprint_redistribute_tasks

Revision ID: e3859e843f7f
Revises: 254d084a536e
Create Date: 2026-02-10 17:37:24.722182

Creates a Backlog sprint and redistributes tasks to achieve:
- Done sprint (Sprint 1): 10 tasks (25.6%)
- Backlog sprint (Sprint 3): 8 tasks (20.5%)
- Active sprint (Sprint 2): 21 tasks (53.8%)

Only runs when SEED_MOCK_DATA=true environment variable is set.

Usage:
    SEED_MOCK_DATA=true uv run alembic upgrade head
"""

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3859e843f7f"
down_revision: str | Sequence[str] | None = "254d084a536e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# =============================================================================
# CONSTANTS
# =============================================================================

# UUIDs for entities
UUIDS = {
    # Organization
    "org_acme": "00000010-0000-0000-0001-000000000010",
    # Sprints
    "sprint_1": "00000060-0000-0000-0001-000000000060",
    "sprint_2": "00000060-0000-0000-0002-000000000060",
    "sprint_3": "00000060-0000-0000-0003-000000000060",
    # Tasks
    "task_1": "00000010-0000-0000-0001-000000000001",
    "task_2": "00000010-0000-0000-0001-000000000002",
    "task_3": "00000010-0000-0000-0001-000000000003",
    "task_4": "00000010-0000-0000-0001-000000000004",
    "task_5": "00000010-0000-0000-0001-000000000005",
    "task_6": "00000010-0000-0000-0001-000000000006",
    "task_7": "00000010-0000-0000-0001-000000000007",
    "task_8": "00000010-0000-0000-0001-000000000008",
    "task_9": "00000010-0000-0000-0001-000000000009",
    "task_10": "00000010-0000-0000-0001-000000000010",
    "task_11": "00000010-0000-0000-0001-000000000011",
    "task_12": "00000010-0000-0000-0001-000000000012",
    "task_13": "00000010-0000-0000-0001-000000000013",
    "task_14": "00000010-0000-0000-0001-000000000014",
    "task_15": "00000010-0000-0000-0001-000000000015",
    "task_16": "00000010-0000-0000-0001-000000000016",
    "task_17": "00000010-0000-0000-0001-000000000017",
    "task_18": "00000010-0000-0000-0001-000000000018",
    "task_19": "00000010-0000-0000-0001-000000000019",
    "task_20": "00000010-0000-0000-0001-000000000020",
    "task_21": "00000010-0000-0000-0001-000000000021",
    "task_22": "00000010-0000-0000-0001-000000000022",
    "task_23": "00000010-0000-0000-0001-000000000023",
    "task_24": "00000010-0000-0000-0001-000000000024",
    "task_25": "00000010-0000-0000-0001-000000000025",
    "task_26": "00000010-0000-0000-0001-000000000026",
    "task_27": "00000010-0000-0000-0001-000000000027",
    "task_28": "00000010-0000-0000-0001-000000000028",
    "task_29": "00000010-0000-0000-0001-000000000029",
    "task_30": "00000010-0000-0000-0001-000000000030",
    "task_31": "00000010-0000-0000-0001-000000000031",
    "task_32": "00000010-0000-0000-0001-000000000032",
    "task_33": "00000010-0000-0000-0001-000000000033",
    "task_34": "00000010-0000-0000-0001-000000000034",
    "task_35": "00000010-0000-0000-0001-000000000035",
    "task_36": "00000010-0000-0000-0001-000000000036",
    "task_37": "00000010-0000-0000-0001-000000000037",
    "task_38": "00000010-0000-0000-0001-000000000038",
    "task_39": "00000010-0000-0000-0001-000000000039",
}

# Root user UUID (for created_by / last_modified_by)
ROOT_USER = "00000000-0000-0000-0000-000000000000"

# Timestamp for all records
TIMESTAMP = "2025-01-15 10:00:00.000000"

# Task distribution
# Done Sprint (Sprint 1) - add 7 tasks (already has task_4, task_5, task_10)
SPRINT_1_NEW_TASKS = ["task_28", "task_34", "task_35", "task_36", "task_37", "task_38", "task_39"]

# Backlog Sprint (Sprint 3) - 8 tasks
SPRINT_3_TASKS = ["task_2", "task_7", "task_12", "task_14", "task_15", "task_16", "task_17", "task_18"]

# Active Sprint (Sprint 2) - add 16 tasks (already has task_1, task_3, task_6, task_8, task_9)
SPRINT_2_NEW_TASKS = [
    "task_11", "task_13", "task_19", "task_20", "task_21", "task_22",
    "task_23", "task_24", "task_25", "task_26", "task_27", "task_29",
    "task_30", "task_31", "task_32", "task_33",
]


# =============================================================================
# UPGRADE
# =============================================================================


def upgrade() -> None:
    """Upgrade schema - add backlog sprint and redistribute tasks."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping backlog sprint creation. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Adding backlog sprint and redistributing tasks...")

    _insert_backlog_sprint()
    _insert_sprint_tasks()

    print("Backlog sprint creation and task redistribution complete!")


def _insert_backlog_sprint() -> None:
    """Insert Sprint 3 - Backlog."""
    org_id = UUIDS["org_acme"]
    sprint_uuid = UUIDS["sprint_3"]

    op.execute(f"""
        INSERT INTO k_sprint (
            id, org_id, title, status, end_ts, meta, deleted_at,
            created, created_by, last_modified, last_modified_by
        ) VALUES (
            '{sprint_uuid}'::uuid, '{org_id}'::uuid, 'Backlog', 'BACKLOG',
            NULL, '{{}}', NULL,
            '{TIMESTAMP}', '{ROOT_USER}'::uuid,
            '{TIMESTAMP}', '{ROOT_USER}'::uuid
        )
    """)


def _insert_sprint_tasks() -> None:
    """Link tasks to sprints."""
    org_id = UUIDS["org_acme"]

    # Add new tasks to Sprint 1 (Done)
    sprint_1_uuid = UUIDS["sprint_1"]
    for task_key in SPRINT_1_NEW_TASKS:
        task_uuid = UUIDS[task_key]
        op.execute(f"""
            INSERT INTO k_sprint_task (
                sprint_id, task_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{sprint_1_uuid}'::uuid, '{task_uuid}'::uuid, '{org_id}'::uuid,
                'included', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)

    # Add all tasks to Sprint 3 (Backlog)
    sprint_3_uuid = UUIDS["sprint_3"]
    for task_key in SPRINT_3_TASKS:
        task_uuid = UUIDS[task_key]
        op.execute(f"""
            INSERT INTO k_sprint_task (
                sprint_id, task_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{sprint_3_uuid}'::uuid, '{task_uuid}'::uuid, '{org_id}'::uuid,
                'included', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)

    # Add new tasks to Sprint 2 (Active)
    sprint_2_uuid = UUIDS["sprint_2"]
    for task_key in SPRINT_2_NEW_TASKS:
        task_uuid = UUIDS[task_key]
        op.execute(f"""
            INSERT INTO k_sprint_task (
                sprint_id, task_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{sprint_2_uuid}'::uuid, '{task_uuid}'::uuid, '{org_id}'::uuid,
                'included', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


# =============================================================================
# DOWNGRADE
# =============================================================================


def downgrade() -> None:
    """Downgrade schema - remove backlog sprint and new sprint-task relationships."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping backlog sprint removal. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Removing backlog sprint and new sprint-task relationships...")

    _delete_new_sprint_tasks()
    _delete_backlog_sprint()

    print("Backlog sprint removal complete!")


def _delete_new_sprint_tasks() -> None:
    """Delete sprint-task relationships added by this migration."""
    # Delete new Sprint 1 tasks
    sprint_1_uuid = UUIDS["sprint_1"]
    for task_key in SPRINT_1_NEW_TASKS:
        task_uuid = UUIDS[task_key]
        op.execute(f"""
            DELETE FROM k_sprint_task
            WHERE sprint_id = '{sprint_1_uuid}'::uuid AND task_id = '{task_uuid}'::uuid
        """)

    # Delete all Sprint 3 tasks
    sprint_3_uuid = UUIDS["sprint_3"]
    op.execute(f"DELETE FROM k_sprint_task WHERE sprint_id = '{sprint_3_uuid}'::uuid")

    # Delete new Sprint 2 tasks
    sprint_2_uuid = UUIDS["sprint_2"]
    for task_key in SPRINT_2_NEW_TASKS:
        task_uuid = UUIDS[task_key]
        op.execute(f"""
            DELETE FROM k_sprint_task
            WHERE sprint_id = '{sprint_2_uuid}'::uuid AND task_id = '{task_uuid}'::uuid
        """)


def _delete_backlog_sprint() -> None:
    """Delete Sprint 3 - Backlog."""
    sprint_uuid = UUIDS["sprint_3"]
    op.execute(f"DELETE FROM k_sprint WHERE id = '{sprint_uuid}'::uuid")
