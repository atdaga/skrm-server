"""seed_mock_data

Revision ID: fb17ad7f0ddc
Revises: 353556ff2f4b
Create Date: 2025-12-20 23:03:33.044222

Seeds mock data for development/testing purposes.
Only runs when SEED_MOCK_DATA=true environment variable is set.

Usage:
    SEED_MOCK_DATA=true uv run alembic upgrade head
"""

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb17ad7f0ddc"
down_revision: str | Sequence[str] | None = "353556ff2f4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# =============================================================================
# CONSTANTS
# =============================================================================

# Deterministic UUIDs for mock data
# Format: XXXXXXXX-0000-0000-SSSS-TTTTTTTTTTTT
# XXXXXXXX = Entity type, SSSS = Sequence, TTTTTTTTTTTT = Type suffix
UUIDS = {
    # Users (00000001-...-000000000001)
    "user_alice": "00000001-0000-0000-0001-000000000001",
    "user_bob": "00000001-0000-0000-0002-000000000001",
    "user_charlie": "00000001-0000-0000-0003-000000000001",
    "user_diana": "00000001-0000-0000-0004-000000000001",
    "user_eve": "00000001-0000-0000-0005-000000000001",
    # User Identities (00000002-...-000000000002)
    "identity_alice": "00000002-0000-0000-0001-000000000002",
    "identity_bob": "00000002-0000-0000-0002-000000000002",
    "identity_charlie": "00000002-0000-0000-0003-000000000002",
    "identity_diana": "00000002-0000-0000-0004-000000000002",
    "identity_eve": "00000002-0000-0000-0005-000000000002",
    # Organization (00000010-...-000000000010)
    "org_acme": "00000010-0000-0000-0001-000000000010",
    # Projects (00000020-...-000000000020)
    "project_alpha": "00000020-0000-0000-0001-000000000020",
    "project_beta": "00000020-0000-0000-0002-000000000020",
    # Teams (00000030-...-000000000030)
    "team_frontend": "00000030-0000-0000-0001-000000000030",
    "team_backend": "00000030-0000-0000-0002-000000000030",
    "team_platform": "00000030-0000-0000-0003-000000000030",
    # Features (00000040-...-000000000040)
    "feature_user_mgmt": "00000040-0000-0000-0001-000000000040",
    "feature_user_auth": "00000040-0000-0000-0002-000000000040",
    "feature_user_profiles": "00000040-0000-0000-0003-000000000040",
    "feature_dashboard": "00000040-0000-0000-0004-000000000040",
    "feature_analytics": "00000040-0000-0000-0005-000000000040",
    "feature_notifications": "00000040-0000-0000-0006-000000000040",
    "feature_api_gateway": "00000040-0000-0000-0007-000000000040",
    "feature_mobile_app": "00000040-0000-0000-0008-000000000040",
    # Tasks (00000050-...-000000000050)
    "task_1": "00000050-0000-0000-0001-000000000050",
    "task_2": "00000050-0000-0000-0002-000000000050",
    "task_3": "00000050-0000-0000-0003-000000000050",
    "task_4": "00000050-0000-0000-0004-000000000050",
    "task_5": "00000050-0000-0000-0005-000000000050",
    "task_6": "00000050-0000-0000-0006-000000000050",
    "task_7": "00000050-0000-0000-0007-000000000050",
    "task_8": "00000050-0000-0000-0008-000000000050",
    "task_9": "00000050-0000-0000-0009-000000000050",
    "task_10": "00000050-0000-0000-000a-000000000050",
    # Sprints (00000060-...-000000000060)
    "sprint_1": "00000060-0000-0000-0001-000000000060",
    "sprint_2": "00000060-0000-0000-0002-000000000060",
    # Deployment Environments (00000070-...-000000000070)
    "env_dev": "00000070-0000-0000-0001-000000000070",
    "env_staging": "00000070-0000-0000-0002-000000000070",
    "env_prod": "00000070-0000-0000-0003-000000000070",
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
    """Upgrade schema - seed mock data for development/testing."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping mock data seeding. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Seeding mock data for development/testing...")

    _insert_users()
    _insert_user_identities()
    _insert_organization()
    _insert_organization_principals()
    _insert_teams()
    _insert_team_members()
    _insert_projects()
    _insert_project_teams()
    _insert_features()
    _insert_tasks()
    _insert_task_owners()
    _insert_task_features()
    _insert_deployment_envs()
    _insert_sprints()
    _insert_sprint_tasks()
    _insert_sprint_teams()

    print("Mock data seeding complete!")


def _insert_users() -> None:
    """Insert mock users into k_principal."""
    users = [
        ("alice", "alice@example.com", "Alice", "Anderson", "Alice Anderson", "systemUser"),
        ("bob", "bob@example.com", "Bob", "Builder", "Bob Builder", "systemUser"),
        ("charlie", "charlie@example.com", "Charlie", "Chen", "Charlie Chen", "systemUser"),
        ("diana", "diana@example.com", "Diana", "Davis", "Diana Davis", "systemAdmin"),
        ("eve", "eve@example.com", "Eve", "Evans", "Eve Evans", "systemUser"),
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


def _insert_user_identities() -> None:
    """Insert password identities for mock users."""
    users = ["alice", "bob", "charlie", "diana", "eve"]
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


def _insert_organization() -> None:
    """Insert mock organization."""
    op.execute(f"""
        INSERT INTO k_organization (
            id, name, alias, meta, deleted_at,
            created, created_by, last_modified, last_modified_by
        ) VALUES (
            '{UUIDS["org_acme"]}'::uuid, 'Acme Corporation', 'acme',
            '{{}}', NULL, '{TIMESTAMP}', '{ROOT_USER}'::uuid,
            '{TIMESTAMP}', '{ROOT_USER}'::uuid
        )
    """)


def _insert_organization_principals() -> None:
    """Link all mock users to the organization."""
    users = ["alice", "bob", "charlie", "diana", "eve"]
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


def _insert_teams() -> None:
    """Insert mock teams."""
    teams = [
        ("team_frontend", "Frontend"),
        ("team_backend", "Backend"),
        ("team_platform", "Platform"),
    ]
    org_id = UUIDS["org_acme"]
    for key, name in teams:
        uuid = UUIDS[key]
        op.execute(f"""
            INSERT INTO k_team (
                id, org_id, name, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{name}', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_team_members() -> None:
    """Assign users to teams."""
    # Frontend: Alice, Bob
    # Backend: Bob, Charlie
    # Platform: Diana, Eve
    memberships = [
        ("team_frontend", "user_alice"),
        ("team_frontend", "user_bob"),
        ("team_backend", "user_bob"),
        ("team_backend", "user_charlie"),
        ("team_platform", "user_diana"),
        ("team_platform", "user_eve"),
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


def _insert_projects() -> None:
    """Insert mock projects."""
    projects = [
        ("project_alpha", "Project Alpha", "Core platform development - backend services and infrastructure"),
        ("project_beta", "Project Beta", "Customer-facing mobile application with real-time features"),
    ]
    org_id = UUIDS["org_acme"]
    for key, name, description in projects:
        uuid = UUIDS[key]
        op.execute(f"""
            INSERT INTO k_project (
                id, org_id, name, description, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{name}', '{description}',
                '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_project_teams() -> None:
    """Link teams to projects."""
    # Project Alpha: Frontend, Backend
    # Project Beta: Frontend, Platform
    links = [
        ("project_alpha", "team_frontend"),
        ("project_alpha", "team_backend"),
        ("project_beta", "team_frontend"),
        ("project_beta", "team_platform"),
    ]
    org_id = UUIDS["org_acme"]
    for proj_key, team_key in links:
        proj_uuid = UUIDS[proj_key]
        team_uuid = UUIDS[team_key]
        op.execute(f"""
            INSERT INTO k_project_team (
                project_id, team_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{proj_uuid}'::uuid, '{team_uuid}'::uuid, '{org_id}'::uuid,
                'contributor', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_features() -> None:
    """Insert mock features with hierarchy."""
    org_id = UUIDS["org_acme"]

    # Parent features first (no parent)
    parent_features = [
        ("feature_user_mgmt", "User Management", "Product", "Complete user management system", None),
        ("feature_dashboard", "Dashboard", "Product", "Main application dashboard with widgets", None),
        ("feature_api_gateway", "API Gateway", "Engineering", "Centralized API gateway for all services", None),
        ("feature_mobile_app", "Mobile App", "Product", "Native mobile application for iOS and Android", None),
    ]

    for key, name, ftype, summary, _parent in parent_features:
        uuid = UUIDS[key]
        op.execute(f"""
            INSERT INTO k_feature (
                id, org_id, name, parent, parent_path, feature_type,
                summary, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{name}', NULL, NULL, '{ftype}',
                '{summary}', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)

    # Child features (with parent)
    child_features = [
        ("feature_user_auth", "User Authentication", "Engineering", "OAuth2, JWT, and session management", "feature_user_mgmt"),
        ("feature_user_profiles", "User Profiles", "Engineering", "User profile CRUD and avatar management", "feature_user_mgmt"),
        ("feature_analytics", "Analytics Widget", "Engineering", "Real-time analytics and charts", "feature_dashboard"),
        ("feature_notifications", "Notification Center", "Engineering", "In-app and push notification system", "feature_dashboard"),
    ]

    for key, name, ftype, summary, parent_key in child_features:
        uuid = UUIDS[key]
        parent_uuid = UUIDS[parent_key]
        op.execute(f"""
            INSERT INTO k_feature (
                id, org_id, name, parent, parent_path, feature_type,
                summary, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{name}',
                '{parent_uuid}'::uuid, '/{parent_uuid}', '{ftype}',
                '{summary}', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_tasks() -> None:
    """Insert mock tasks with various statuses."""
    org_id = UUIDS["org_acme"]

    # (key, summary, description, team_key, status, guestimate)
    tasks = [
        ("task_1", "Implement login form", "Create responsive login form with email/password fields and validation", "team_frontend", "InProgress", 3.0),
        ("task_2", "Add OAuth2 support", "Integrate OAuth2 authentication with Google and GitHub providers", "team_backend", "Backlog", 5.0),
        ("task_3", "Create user avatar upload", "Allow users to upload and crop profile avatars with size limits", "team_frontend", "OnDeck", 2.0),
        ("task_4", "Design database schema", "Create ERD and implement PostgreSQL schema for user management", "team_backend", "Completed", 4.0),
        ("task_5", "Set up CI/CD pipeline", "Configure GitHub Actions for automated testing and deployment", "team_platform", "Done", 8.0),
        ("task_6", "Build analytics dashboard", "Create interactive dashboard with charts and real-time updates", "team_frontend", "InProgress", 6.0),
        ("task_7", "Implement caching layer", "Add Redis caching for frequently accessed data and sessions", "team_backend", "Backlog", 4.0),
        ("task_8", "Add rate limiting", "Implement API rate limiting to prevent abuse and ensure fair usage", "team_platform", "Review", 3.0),
        ("task_9", "Create notification API", "Build REST API endpoints for managing user notifications", "team_backend", "OnDeck", 4.0),
        ("task_10", "Deploy staging environment", "Set up staging environment with Docker and Kubernetes", "team_platform", "Deployed", 2.0),
    ]

    for key, summary, description, team_key, status, guestimate in tasks:
        uuid = UUIDS[key]
        team_uuid = UUIDS[team_key]
        op.execute(f"""
            INSERT INTO k_task (
                id, org_id, summary, description, team_id, guestimate, status,
                meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{summary}', '{description}',
                '{team_uuid}'::uuid, {guestimate}, '{status}',
                '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_task_owners() -> None:
    """Assign owners to tasks based on team membership."""
    org_id = UUIDS["org_acme"]

    # Task owners based on team assignments
    owners = [
        ("task_1", "user_alice"),  # Frontend task -> Alice
        ("task_2", "user_charlie"),  # Backend task -> Charlie
        ("task_3", "user_bob"),  # Frontend task -> Bob
        ("task_4", "user_charlie"),  # Backend task -> Charlie
        ("task_5", "user_diana"),  # Platform task -> Diana
        ("task_6", "user_alice"),  # Frontend task -> Alice
        ("task_6", "user_bob"),  # Also Bob (pair work)
        ("task_7", "user_bob"),  # Backend task -> Bob
        ("task_8", "user_eve"),  # Platform task -> Eve
        ("task_9", "user_charlie"),  # Backend task -> Charlie
        ("task_10", "user_diana"),  # Platform task -> Diana
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


def _insert_task_features() -> None:
    """Link tasks to features."""
    org_id = UUIDS["org_acme"]

    links = [
        ("task_1", "feature_user_auth"),  # Login form -> User Auth
        ("task_2", "feature_user_auth"),  # OAuth2 -> User Auth
        ("task_3", "feature_user_profiles"),  # Avatar upload -> User Profiles
        ("task_4", "feature_user_mgmt"),  # DB schema -> User Management
        ("task_5", "feature_api_gateway"),  # CI/CD -> API Gateway
        ("task_6", "feature_analytics"),  # Analytics dashboard -> Analytics Widget
        ("task_7", "feature_api_gateway"),  # Caching -> API Gateway
        ("task_8", "feature_api_gateway"),  # Rate limiting -> API Gateway
        ("task_9", "feature_notifications"),  # Notification API -> Notifications
        ("task_10", "feature_api_gateway"),  # Staging deploy -> API Gateway
    ]

    for task_key, feature_key in links:
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


def _insert_deployment_envs() -> None:
    """Insert deployment environments."""
    org_id = UUIDS["org_acme"]

    envs = [
        ("env_dev", "Development"),
        ("env_staging", "Staging"),
        ("env_prod", "Production"),
    ]

    for key, name in envs:
        uuid = UUIDS[key]
        op.execute(f"""
            INSERT INTO k_deployment_env (
                id, org_id, name, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{name}', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_sprints() -> None:
    """Insert mock sprints."""
    org_id = UUIDS["org_acme"]

    # Sprint 1: Done (ended 2 weeks ago)
    # Sprint 2: Active (ends in 2 weeks)
    # Note: PostgreSQL enum uses uppercase values
    sprints = [
        ("sprint_1", "Sprint 1 - Foundation", "DONE", "2025-01-01 17:00:00"),
        ("sprint_2", "Sprint 2 - Core Features", "ACTIVE", "2025-01-29 17:00:00"),
    ]

    for key, title, status, end_ts in sprints:
        uuid = UUIDS[key]
        op.execute(f"""
            INSERT INTO k_sprint (
                id, org_id, title, status, end_ts, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{uuid}'::uuid, '{org_id}'::uuid, '{title}', '{status}',
                '{end_ts}', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_sprint_tasks() -> None:
    """Link tasks to sprints."""
    org_id = UUIDS["org_acme"]

    # Sprint 1 (Done): Completed/Done/Deployed tasks
    # Sprint 2 (Active): In progress and pending tasks
    links = [
        ("sprint_1", "task_4"),  # Completed
        ("sprint_1", "task_5"),  # Done
        ("sprint_1", "task_10"),  # Deployed
        ("sprint_2", "task_1"),  # InProgress
        ("sprint_2", "task_3"),  # OnDeck
        ("sprint_2", "task_6"),  # InProgress
        ("sprint_2", "task_8"),  # Review
        ("sprint_2", "task_9"),  # OnDeck
    ]

    for sprint_key, task_key in links:
        sprint_uuid = UUIDS[sprint_key]
        task_uuid = UUIDS[task_key]
        op.execute(f"""
            INSERT INTO k_sprint_task (
                sprint_id, task_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{sprint_uuid}'::uuid, '{task_uuid}'::uuid, '{org_id}'::uuid,
                'included', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


def _insert_sprint_teams() -> None:
    """Link teams to sprints."""
    org_id = UUIDS["org_acme"]

    # Sprint 1: All teams participated
    # Sprint 2: Frontend and Backend (Platform finished their work)
    links = [
        ("sprint_1", "team_frontend"),
        ("sprint_1", "team_backend"),
        ("sprint_1", "team_platform"),
        ("sprint_2", "team_frontend"),
        ("sprint_2", "team_backend"),
    ]

    for sprint_key, team_key in links:
        sprint_uuid = UUIDS[sprint_key]
        team_uuid = UUIDS[team_key]
        op.execute(f"""
            INSERT INTO k_sprint_team (
                sprint_id, team_id, org_id, role, meta, deleted_at,
                created, created_by, last_modified, last_modified_by
            ) VALUES (
                '{sprint_uuid}'::uuid, '{team_uuid}'::uuid, '{org_id}'::uuid,
                'participating', '{{}}', NULL,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid,
                '{TIMESTAMP}', '{ROOT_USER}'::uuid
            )
        """)


# =============================================================================
# DOWNGRADE
# =============================================================================


def downgrade() -> None:
    """Downgrade schema - remove mock data."""
    if os.getenv("SEED_MOCK_DATA", "false").lower() != "true":
        print("Skipping mock data removal. Set SEED_MOCK_DATA=true to enable.")
        return

    print("Removing mock data...")

    org_id = UUIDS["org_acme"]

    # Delete in reverse FK order (junction tables first, then entities)

    # 1. Sprint associations
    op.execute(f"DELETE FROM k_sprint_team WHERE org_id = '{org_id}'")
    op.execute(f"DELETE FROM k_sprint_task WHERE org_id = '{org_id}'")

    # 2. Sprints
    for key in ["sprint_1", "sprint_2"]:
        op.execute(f"DELETE FROM k_sprint WHERE id = '{UUIDS[key]}'")

    # 3. Deployment environments
    for key in ["env_dev", "env_staging", "env_prod"]:
        op.execute(f"DELETE FROM k_deployment_env WHERE id = '{UUIDS[key]}'")

    # 4. Task associations
    op.execute(f"DELETE FROM k_task_feature WHERE org_id = '{org_id}'")
    op.execute(f"DELETE FROM k_task_owner WHERE org_id = '{org_id}'")

    # 5. Tasks
    for i in range(1, 11):
        key = f"task_{i}"
        op.execute(f"DELETE FROM k_task WHERE id = '{UUIDS[key]}'")

    # 6. Features (delete children before parents due to FK)
    child_features = [
        "feature_user_auth",
        "feature_user_profiles",
        "feature_analytics",
        "feature_notifications",
    ]
    for key in child_features:
        op.execute(f"DELETE FROM k_feature WHERE id = '{UUIDS[key]}'")

    parent_features = [
        "feature_user_mgmt",
        "feature_dashboard",
        "feature_api_gateway",
        "feature_mobile_app",
    ]
    for key in parent_features:
        op.execute(f"DELETE FROM k_feature WHERE id = '{UUIDS[key]}'")

    # 7. Project-team associations
    op.execute(f"DELETE FROM k_project_team WHERE org_id = '{org_id}'")

    # 8. Projects
    for key in ["project_alpha", "project_beta"]:
        op.execute(f"DELETE FROM k_project WHERE id = '{UUIDS[key]}'")

    # 9. Team members
    op.execute(f"DELETE FROM k_team_member WHERE org_id = '{org_id}'")

    # 10. Teams
    for key in ["team_frontend", "team_backend", "team_platform"]:
        op.execute(f"DELETE FROM k_team WHERE id = '{UUIDS[key]}'")

    # 11. Organization-principal associations
    op.execute(f"DELETE FROM k_organization_principal WHERE org_id = '{org_id}'")

    # 12. Organization
    op.execute(f"DELETE FROM k_organization WHERE id = '{org_id}'")

    # 13. User identities
    for username in ["alice", "bob", "charlie", "diana", "eve"]:
        key = f"identity_{username}"
        op.execute(f"DELETE FROM k_principal_identity WHERE id = '{UUIDS[key]}'")

    # 14. Users
    for username in ["alice", "bob", "charlie", "diana", "eve"]:
        key = f"user_{username}"
        op.execute(f"DELETE FROM k_principal WHERE id = '{UUIDS[key]}'")

    print("Mock data removal complete!")
