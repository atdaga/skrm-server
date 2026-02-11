"""seed_extended_mock_data

Revision ID: 254d084a536e
Revises: fb17ad7f0ddc
Create Date: 2026-02-10 17:09:48.323032

Extended seed data for development/testing purposes:
- 2 new users (Frank, Grace)
- QA team with Frank and Grace as members
- 26 new tasks (39 total)
- Task reviewers for appropriate tasks
- Task deployment records

Only runs when SEED_MOCK_DATA=true environment variable is set.

Usage:
    SEED_MOCK_DATA=true uv run alembic upgrade head
"""

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "254d084a536e"
down_revision: str | Sequence[str] | None = "fb17ad7f0ddc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# =============================================================================
# CONSTANTS (from original seed migration)
# =============================================================================

# Original UUIDs from seed_mock_data migration
UUIDS = {
    # Users
    "user_alice": "00000001-0000-0000-0001-000000000001",
    "user_bob": "00000001-0000-0000-0002-000000000001",
    "user_charlie": "00000001-0000-0000-0003-000000000001",
    "user_diana": "00000001-0000-0000-0004-000000000001",
    "user_eve": "00000001-0000-0000-0005-000000000001",
    # New users
    "user_frank": "00000001-0000-0000-0006-000000000001",
    "user_grace": "00000001-0000-0000-0007-000000000001",
    # User Identities (new)
    "identity_frank": "00000002-0000-0000-0006-000000000002",
    "identity_grace": "00000002-0000-0000-0007-000000000002",
    # Organization
    "org_acme": "00000010-0000-0000-0001-000000000010",
    # Teams
    "team_frontend": "00000030-0000-0000-0001-000000000030",
    "team_backend": "00000030-0000-0000-0002-000000000030",
    "team_platform": "00000030-0000-0000-0003-000000000030",
    "team_qa": "00000030-0000-0000-0004-000000000030",
    # Deployment Environments
    "env_dev": "00000070-0000-0000-0001-000000000070",
    "env_staging": "00000070-0000-0000-0002-000000000070",
    "env_prod": "00000070-0000-0000-0003-000000000070",
    # Existing tasks (1-13)
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
    # New tasks (14-39)
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

# Password hash for P@ssword12
PASSWORD_HASH = "$2b$12$rdK6qPYTy0OEmjrHSlqsv.GSkqqi2gcJJyMIsMma.SeQS1HwqG002"

# Timestamp for all records
TIMESTAMP = "2025-01-15 10:00:00.000000"


# =============================================================================
# UPGRADE
# =============================================================================


def upgrade() -> None:
    """Upgrade schema - seed extended mock data for development/testing."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping extended mock data seeding. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Seeding extended mock data for development/testing...")

    _insert_new_users()
    _insert_new_user_identities()
    _insert_new_org_principals()
    _insert_qa_team()
    _insert_qa_team_members()
    _insert_new_tasks()
    _insert_new_task_owners()
    _insert_task_reviewers()
    _insert_task_deployments()

    print("Extended mock data seeding complete!")


def _insert_new_users() -> None:
    """Insert new mock users (Frank, Grace) into k_principal."""
    users = [
        ("frank", "frank@example.com", "Frank", "Fischer", "Frank Fischer", "systemUser"),
        ("grace", "grace@example.com", "Grace", "Garcia", "Grace Garcia", "systemUser"),
    ]
    for username, email, first, last, display, role in users:
        uuid = UUIDS[f"user_{username}"]
        op.execute(f"""
            INSERT INTO k_principal (
                id, scope, username, primary_email, primary_email_verified,
                primary_phone_verified, human, enabled, time_zone,
                first_name, last_name, display_name, default_locale,
                system_role, meta, deleted_at, created, created_by,
                last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, 'global', '{username}', '{email}', false,
                false, true, true, 'UTC',
                '{first}', '{last}', '{display}', 'en',
                '{role}', '{{}}', NULL, '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_new_user_identities() -> None:
    """Insert password identities for new mock users."""
    users = ["frank", "grace"]
    for username in users:
        user_uuid = UUIDS[f"user_{username}"]
        identity_uuid = UUIDS[f"identity_{username}"]
        op.execute(f"""
            INSERT INTO k_principal_identity (
                id, principal_id, password, details,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{identity_uuid}'::uuid, '{user_uuid}'::uuid,
                '{PASSWORD_HASH}', '{{}}',
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_new_org_principals() -> None:
    """Link new mock users to the organization."""
    users = ["frank", "grace"]
    org_id = UUIDS["org_acme"]
    for username in users:
        user_uuid = UUIDS[f"user_{username}"]
        op.execute(f"""
            INSERT INTO k_organization_principal (
                org_id, principal_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{org_id}'::uuid, '{user_uuid}'::uuid, 'member', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_qa_team() -> None:
    """Insert QA team."""
    org_id = UUIDS["org_acme"]
    uuid = UUIDS["team_qa"]
    op.execute(f"""
        INSERT INTO k_team (
            id, org_id, name, meta, deleted_at,
            created, created_by, last_modified, last_modified_by
        ) VALUES (
            '{uuid}'::uuid, '{org_id}'::uuid, 'QA', '{{}}', NULL,
            '{TIMESTAMP}', '{ROOT_USER}'::uuid,
            '{TIMESTAMP}', '{ROOT_USER}'::uuid
        )
    """)


def _insert_qa_team_members() -> None:
    """Assign Frank and Grace to QA team."""
    memberships = [
        ("team_qa", "user_frank"),
        ("team_qa", "user_grace"),
    ]
    org_id = UUIDS["org_acme"]
    for team_key, user_key in memberships:
        team_uuid = UUIDS[team_key]
        user_uuid = UUIDS[user_key]
        op.execute(f"""
            INSERT INTO k_team_member (
                team_id, principal_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{team_uuid}'::uuid, '{user_uuid}'::uuid, '{org_id}'::uuid,
                'member', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_new_tasks() -> None:
    """Insert 26 new mock tasks with various statuses."""
    org_id = UUIDS["org_acme"]

    # (key, summary, description, team_key, status, guestimate)
    tasks = [
        # BACKLOG (5 new)
        ("task_14", "Implement SSO integration", "Integrate single sign-on with enterprise identity providers", "team_backend", "Backlog", 6.0),
        ("task_15", "Create user settings page", "Build comprehensive user preferences and settings interface", "team_frontend", "Backlog", 4.0),
        ("task_16", "Add monitoring dashboard", "Create infrastructure monitoring dashboard with alerts", "team_platform", "Backlog", 5.0),
        ("task_17", "Build notification preferences UI", "User interface for managing notification preferences", "team_frontend", "Backlog", 3.0),
        ("task_18", "Create test automation framework", "Build end-to-end test automation framework", "team_qa", "Backlog", 8.0),
        # ON_DECK (3 new)
        ("task_19", "Add API documentation generator", "Automated OpenAPI documentation generation from code", "team_backend", "OnDeck", 3.0),
        ("task_20", "Build accessibility checker", "Automated accessibility compliance checking tool", "team_qa", "OnDeck", 5.0),
        ("task_21", "Create performance benchmarks", "Establish and track performance benchmark suite", "team_platform", "OnDeck", 4.0),
        # IN_PROGRESS (3 new)
        ("task_22", "Implement GraphQL endpoint", "Add GraphQL API alongside existing REST endpoints", "team_backend", "InProgress", 7.0),
        ("task_23", "Build log aggregation service", "Centralized log collection and analysis service", "team_platform", "InProgress", 6.0),
        ("task_24", "Create integration test suite", "Comprehensive integration tests for all API endpoints", "team_qa", "InProgress", 5.0),
        # COMPLETED (3 new)
        ("task_25", "Add user search functionality", "Full-text search across user profiles and content", "team_frontend", "Completed", 3.0),
        ("task_26", "Implement audit logging", "Comprehensive audit trail for all system actions", "team_backend", "Completed", 4.0),
        ("task_27", "Create security scanning pipeline", "Automated security vulnerability scanning in CI/CD", "team_qa", "Completed", 5.0),
        # DEPLOYED (3 new)
        ("task_28", "Deploy user authentication service", "Production deployment of auth microservice", "team_backend", "Deployed", 2.0),
        ("task_29", "Deploy CDN configuration", "Global CDN setup for static assets", "team_platform", "Deployed", 3.0),
        ("task_30", "Deploy QA test environment", "Dedicated QA testing environment with data fixtures", "team_qa", "Deployed", 4.0),
        # REVIEW (3 new)
        ("task_31", "Review form validation library", "Code review for new form validation components", "team_frontend", "Review", 4.0),
        ("task_32", "Review database indexing strategy", "Review and optimize database index configuration", "team_backend", "Review", 3.0),
        ("task_33", "Review load testing scripts", "Review performance test scripts and thresholds", "team_qa", "Review", 3.0),
        # DONE (6 new)
        ("task_34", "Complete user onboarding flow", "Full user onboarding experience with tutorials", "team_frontend", "Done", 5.0),
        ("task_35", "Complete API versioning system", "API version management and deprecation handling", "team_backend", "Done", 4.0),
        ("task_36", "Complete Kubernetes cluster setup", "Production-ready K8s cluster with auto-scaling", "team_platform", "Done", 10.0),
        ("task_37", "Complete regression test suite", "Automated regression tests for all features", "team_qa", "Done", 6.0),
        ("task_38", "Complete error tracking integration", "Sentry integration for error monitoring", "team_backend", "Done", 3.0),
        ("task_39", "Complete production readiness checklist", "Documentation and verification of prod requirements", "team_qa", "Done", 4.0),
    ]

    for key, summary, description, team_key, status, guestimate in tasks:
        uuid = UUIDS[key]
        team_uuid = UUIDS[team_key]
        # Escape single quotes in description
        description_escaped = description.replace("'", "''")
        op.execute(f"""
            INSERT INTO k_task (
                id, org_id, summary, description, team_id, guestimate, status,
                meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{summary}', '{description_escaped}',
                '{team_uuid}'::uuid, {guestimate}, '{status}',
                '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_new_task_owners() -> None:
    """Assign owners to new tasks based on team membership."""
    org_id = UUIDS["org_acme"]

    # Task owners for new tasks
    owners = [
        # BACKLOG
        ("task_14", "user_charlie"),  # Backend -> Charlie
        ("task_15", "user_alice"),    # Frontend -> Alice
        ("task_16", "user_diana"),    # Platform -> Diana
        ("task_17", "user_bob"),      # Frontend -> Bob
        ("task_18", "user_frank"),    # QA -> Frank
        # ON_DECK
        ("task_19", "user_bob"),      # Backend -> Bob
        ("task_20", "user_grace"),    # QA -> Grace
        ("task_21", "user_eve"),      # Platform -> Eve
        # IN_PROGRESS
        ("task_22", "user_charlie"),  # Backend -> Charlie
        ("task_23", "user_diana"),    # Platform -> Diana
        ("task_24", "user_frank"),    # QA -> Frank
        # COMPLETED
        ("task_25", "user_alice"),    # Frontend -> Alice
        ("task_26", "user_charlie"),  # Backend -> Charlie
        ("task_27", "user_grace"),    # QA -> Grace
        # DEPLOYED
        ("task_28", "user_bob"),      # Backend -> Bob
        ("task_29", "user_eve"),      # Platform -> Eve
        ("task_30", "user_frank"),    # QA -> Frank
        # REVIEW
        ("task_31", "user_alice"),    # Frontend -> Alice
        ("task_32", "user_charlie"),  # Backend -> Charlie
        ("task_33", "user_grace"),    # QA -> Grace
        # DONE
        ("task_34", "user_bob"),      # Frontend -> Bob
        ("task_35", "user_charlie"),  # Backend -> Charlie
        ("task_36", "user_diana"),    # Platform -> Diana
        ("task_37", "user_frank"),    # QA -> Frank
        ("task_38", "user_bob"),      # Backend -> Bob
        ("task_39", "user_grace"),    # QA -> Grace
    ]

    for task_key, user_key in owners:
        task_uuid = UUIDS[task_key]
        user_uuid = UUIDS[user_key]
        op.execute(f"""
            INSERT INTO k_task_owner (
                task_id, principal_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{task_uuid}'::uuid, '{user_uuid}'::uuid, '{org_id}'::uuid,
                'owner', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_task_reviewers() -> None:
    """Insert task reviewers for appropriate tasks.

    Rules:
    - BACKLOG tasks have NO reviewers
    - COMPLETED, DEPLOYED, REVIEW, DONE tasks MUST have reviewers
    - Some ON_DECK and IN_PROGRESS tasks have reviewers

    Assignment logic:
    - Platform tasks -> QA team (Frank, Grace)
    - Backend tasks -> Backend/Frontend (Alice, Bob, Charlie)
    - Frontend tasks -> Any reviewer
    - QA tasks -> Diana, Eve (Platform team)
    """
    org_id = UUIDS["org_acme"]

    # (task_key, reviewer_user_key)
    reviewers = [
        # Existing tasks (that need reviewers)
        ("task_4", "user_alice"),      # Completed, Backend -> Alice
        ("task_5", "user_frank"),      # Done, Platform -> Frank (QA)
        ("task_8", "user_grace"),      # Review, Platform -> Grace (QA)
        ("task_10", "user_frank"),     # Deployed, Platform -> Frank (QA)
        # Some ON_DECK/IN_PROGRESS existing tasks with reviewers
        ("task_3", "user_charlie"),    # OnDeck, Frontend -> Charlie
        ("task_9", "user_bob"),        # OnDeck, Backend -> Bob
        ("task_11", "user_alice"),     # OnDeck, Backend -> Alice
        # New ON_DECK tasks with reviewers
        ("task_19", "user_charlie"),   # OnDeck, Backend -> Charlie
        ("task_20", "user_diana"),     # OnDeck, QA -> Diana (Platform)
        ("task_21", "user_grace"),     # OnDeck, Platform -> Grace (QA)
        # New IN_PROGRESS tasks with reviewers
        ("task_22", "user_bob"),       # InProgress, Backend -> Bob
        ("task_23", "user_frank"),     # InProgress, Platform -> Frank (QA)
        ("task_24", "user_eve"),       # InProgress, QA -> Eve (Platform)
        # New COMPLETED tasks
        ("task_25", "user_charlie"),   # Completed, Frontend -> Charlie
        ("task_26", "user_alice"),     # Completed, Backend -> Alice
        ("task_26", "user_bob"),       # Completed, Backend -> Bob (second reviewer)
        ("task_27", "user_diana"),     # Completed, QA -> Diana (Platform)
        # New DEPLOYED tasks
        ("task_28", "user_charlie"),   # Deployed, Backend -> Charlie
        ("task_29", "user_grace"),     # Deployed, Platform -> Grace (QA)
        ("task_30", "user_eve"),       # Deployed, QA -> Eve (Platform)
        # New REVIEW tasks
        ("task_31", "user_bob"),       # Review, Frontend -> Bob
        ("task_32", "user_alice"),     # Review, Backend -> Alice
        ("task_33", "user_diana"),     # Review, QA -> Diana (Platform)
        # New DONE tasks
        ("task_34", "user_charlie"),   # Done, Frontend -> Charlie
        ("task_35", "user_bob"),       # Done, Backend -> Bob
        ("task_36", "user_frank"),     # Done, Platform -> Frank (QA)
        ("task_36", "user_grace"),     # Done, Platform -> Grace (QA, second reviewer)
        ("task_37", "user_eve"),       # Done, QA -> Eve (Platform)
        ("task_38", "user_alice"),     # Done, Backend -> Alice
        ("task_39", "user_diana"),     # Done, QA -> Diana (Platform)
        ("task_39", "user_eve"),       # Done, QA -> Eve (Platform, second reviewer)
    ]

    for task_key, user_key in reviewers:
        task_uuid = UUIDS[task_key]
        user_uuid = UUIDS[user_key]
        op.execute(f"""
            INSERT INTO k_task_reviewer (
                task_id, principal_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{task_uuid}'::uuid, '{user_uuid}'::uuid, '{org_id}'::uuid,
                'reviewer', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_task_deployments() -> None:
    """Insert task deployment records.

    All tasks in DEPLOYED, REVIEW, or DONE status must be deployed
    to at least Development environment.
    """
    org_id = UUIDS["org_acme"]

    # (task_key, [env_keys])
    deployments = [
        # Existing tasks
        ("task_5", ["env_dev", "env_staging", "env_prod"]),   # Done
        ("task_8", ["env_dev"]),                               # Review
        ("task_10", ["env_dev"]),                              # Deployed
        # New DEPLOYED tasks
        ("task_28", ["env_dev"]),
        ("task_29", ["env_dev"]),
        ("task_30", ["env_dev"]),
        # New REVIEW tasks
        ("task_31", ["env_dev"]),
        ("task_32", ["env_dev"]),
        ("task_33", ["env_dev"]),
        # New DONE tasks
        ("task_34", ["env_dev", "env_staging", "env_prod"]),
        ("task_35", ["env_dev", "env_staging", "env_prod"]),
        ("task_36", ["env_dev", "env_staging", "env_prod"]),
        ("task_37", ["env_dev", "env_staging"]),
        ("task_38", ["env_dev", "env_staging", "env_prod"]),
        ("task_39", ["env_dev", "env_staging"]),
    ]

    for task_key, env_keys in deployments:
        task_uuid = UUIDS[task_key]
        for env_key in env_keys:
            env_uuid = UUIDS[env_key]
            op.execute(f"""
                INSERT INTO k_task_deployment_env (
                    task_id, deployment_env_id, org_id, role, meta, deleted_at,
                    created, created_by, last_modified, last_modified_by
                ) VALUES (
                    '{task_uuid}'::uuid, '{env_uuid}'::uuid, '{org_id}'::uuid,
                    'deployed', '{{}}', NULL,
                    '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                    '{TIMESTAMP}', '{ROOT_USER}'::uuid
                )
            """)


# =============================================================================
# DOWNGRADE
# =============================================================================


def downgrade() -> None:
    """Downgrade schema - remove extended mock data."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping extended mock data removal. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Removing extended mock data...")

    org_id = UUIDS["org_acme"]

    # Delete in reverse order of insertion (respecting FK constraints)

    # 1. Task deployments
    _delete_task_deployments()

    # 2. Task reviewers
    _delete_task_reviewers()

    # 3. New task owners
    _delete_new_task_owners()

    # 4. New tasks
    _delete_new_tasks()

    # 5. QA team members
    _delete_qa_team_members()

    # 6. QA team
    _delete_qa_team()

    # 7. New org principals
    _delete_new_org_principals()

    # 8. New user identities
    _delete_new_user_identities()

    # 9. New users
    _delete_new_users()

    print("Extended mock data removal complete!")


def _delete_task_deployments() -> None:
    """Delete task deployment records added by this migration."""
    # Delete all deployments for tasks 28-39 and the new deployments for tasks 5, 8, 10
    task_keys = [
        "task_5", "task_8", "task_10",
        "task_28", "task_29", "task_30",
        "task_31", "task_32", "task_33",
        "task_34", "task_35", "task_36", "task_37", "task_38", "task_39",
    ]
    for task_key in task_keys:
        task_uuid = UUIDS[task_key]
        op.execute(f"DELETE FROM k_task_deployment_env WHERE task_id = '{task_uuid}'::uuid")


def _delete_task_reviewers() -> None:
    """Delete all task reviewer records added by this migration."""
    org_id = UUIDS["org_acme"]
    # Delete all reviewers in the org (this migration added all of them)
    op.execute(f"DELETE FROM k_task_reviewer WHERE org_id = '{org_id}'::uuid")


def _delete_new_task_owners() -> None:
    """Delete owners for new tasks."""
    for i in range(14, 40):
        task_key = f"task_{i}"
        task_uuid = UUIDS[task_key]
        op.execute(f"DELETE FROM k_task_owner WHERE task_id = '{task_uuid}'::uuid")


def _delete_new_tasks() -> None:
    """Delete new tasks (14-39)."""
    for i in range(14, 40):
        task_key = f"task_{i}"
        task_uuid = UUIDS[task_key]
        op.execute(f"DELETE FROM k_task WHERE id = '{task_uuid}'::uuid")


def _delete_qa_team_members() -> None:
    """Delete QA team members."""
    team_uuid = UUIDS["team_qa"]
    op.execute(f"DELETE FROM k_team_member WHERE team_id = '{team_uuid}'::uuid")


def _delete_qa_team() -> None:
    """Delete QA team."""
    team_uuid = UUIDS["team_qa"]
    op.execute(f"DELETE FROM k_team WHERE id = '{team_uuid}'::uuid")


def _delete_new_org_principals() -> None:
    """Remove new users from organization."""
    org_id = UUIDS["org_acme"]
    for username in ["frank", "grace"]:
        user_uuid = UUIDS[f"user_{username}"]
        op.execute(f"""
            DELETE FROM k_organization_principal
            WHERE org_id = '{org_id}'::uuid AND principal_id = '{user_uuid}'::uuid
        """)


def _delete_new_user_identities() -> None:
    """Delete password identities for new users."""
    for username in ["frank", "grace"]:
        identity_uuid = UUIDS[f"identity_{username}"]
        op.execute(f"DELETE FROM k_principal_identity WHERE id = '{identity_uuid}'::uuid")


def _delete_new_users() -> None:
    """Delete new users."""
    for username in ["frank", "grace"]:
        user_uuid = UUIDS[f"user_{username}"]
        op.execute(f"DELETE FROM k_principal WHERE id = '{user_uuid}'::uuid")
