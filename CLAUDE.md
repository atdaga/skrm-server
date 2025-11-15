# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development Server
```bash
# Start development server (auto-reload enabled)
uv run scripts/dev.py serve
# Or directly:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests with coverage
uv run pytest -v --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/routes/v1/test_tasks.py -v

# Run specific test function
uv run pytest tests/routes/v1/test_tasks.py::test_create_task -v
```

### Code Quality
```bash
# Format code (black + isort + ruff)
uv run scripts/dev.py format

# Run linting checks
uv run scripts/dev.py lint

# Individual tools
uv run black app tests
uv run isort app tests
uv run ruff check --fix app tests
uv run mypy app
```

### Database Migrations
```bash
# Create new migration (autogenerate from model changes)
uv run scripts/alembic_revision.py "descriptive_name" --autogenerate

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Check current migration version
uv run alembic current
```

### Dependency Management
```bash
# Check if lock file is up-to-date
uv lock --check

# Update lock file after manual pyproject.toml changes
uv lock

# Upgrade all dependencies
uv lock --upgrade && uv sync
```

## Architecture Overview

### Three-Layer Architecture

The application follows a strict three-layer pattern:

1. **Routes Layer** (`app/routes/`): HTTP endpoint handlers
   - Thin wrappers around business logic
   - Handle request/response serialization
   - Convert domain exceptions to HTTP exceptions
   - Use FastAPI dependency injection for auth, DB sessions

2. **Logic Layer** (`app/logic/`): Business logic and validation
   - All business rules and data validation
   - Database queries and transactions
   - Authorization checks (organization membership, permissions)
   - Returns domain models (`KTask`, `KOrganization`, etc.)

3. **Models Layer** (`app/models/`): SQLModel database models
   - Database schema definitions using SQLModel
   - All tables prefixed with `k_` (e.g., `k_task`, `k_principal`)
   - Include audit fields: `created`, `created_by`, `last_modified`, `last_modified_by`, `deleted_at`

### Key Patterns

**Request Flow:**
```
Route Handler → Logic Function → Database → Returns Model → Schema Validation → JSON Response
```

**Example (Task Creation):**
```python
# Route (app/routes/v1/tasks.py)
@router.post("", response_model=TaskDetail)
async def create_task(task_data: TaskCreate, ...):
    task = await tasks_logic.create_task(task_data, user_id, org_id, db)
    return TaskDetail.model_validate(task)

# Logic (app/logic/v1/tasks.py)
async def create_task(task_data, user_id, org_id, db):
    await verify_organization_membership(org_id, user_id, db)
    new_task = KTask(org_id=org_id, created_by=user_id, ...)
    db.add(new_task)
    await db.commit()
    return new_task
```

**Authentication Pattern:**
- JWT tokens with dual refresh strategy (cookies for web, body for mobile)
- Context variables (`app/core/context.py`) populated by middleware for request-scoped data
- Use `get_current_token()` dependency for `TokenData`, `get_current_user()` for `UserDetail`
- Authorization checks in logic layer via `verify_organization_membership()` and role checks

**Exception Handling:**
- Domain exceptions (`app/core/exceptions/domain_exceptions.py`) raised in logic layer
- Converted to HTTP exceptions in route handlers
- Custom exceptions: `TaskNotFoundException`, `UnauthorizedOrganizationAccessException`, etc.

### Database Models

**Naming Convention:**
- All tables prefixed with `k_` (e.g., `k_principal`, `k_task`, `k_organization`)
- Models use SQLModel (combination of SQLAlchemy + Pydantic)

**Standard Audit Fields:**
Every model includes:
- `created: datetime` - Creation timestamp
- `created_by: UUID` - User who created the record
- `last_modified: datetime` - Last modification timestamp
- `last_modified_by: UUID` - User who last modified
- `deleted_at: datetime | None` - Soft delete timestamp

**Soft Deletes:**
All queries must filter `deleted_at.is_(None)` to exclude deleted records.

### Configuration

**Settings Management (`app/config.py`):**
- Pydantic-based settings from `.env` file
- Database URL constructed from individual components
- Security: JWT secrets, token expiration, cookie settings
- FIDO2/WebAuthn: Relying party configuration
- CORS: Origins, credentials, methods
- Debug mode auto-adjusts `cookie_secure` for local development

### Request Context System

The application uses `contextvars` for request-scoped data:

**Available Context Variables:**
- `request_id_var`: UUID for each request
- `principal_id_var`: Authenticated user ID from JWT
- `request_time_var`: Request start timestamp

**Access via:**
```python
from app.core.context import get_request_id, get_principal_id, get_request_time
```

**Populated by:** `RequestContextMiddleware` in `app/core/middleware.py`

### FIDO2/WebAuthn Implementation

Full passwordless and two-factor authentication support:
- Registration/authentication flows for FIDO2 credentials
- Multiple authenticators per user
- Credential lifecycle management (nickname, last used, delete)
- Stored in `k_fido2_credential` table
- See `FIDO2_IMPLEMENTATION.md` for detailed implementation

### Refresh Token Strategy

**Dual Strategy Based on Client Type:**
- **Web (SPA):** Refresh tokens in HTTP-only cookies (XSS protection)
- **Mobile:** Refresh tokens in response body (stored in Keychain/Keystore)

**Client Detection:**
1. `X-Client-Type: mobile` header (preferred)
2. User-Agent patterns (OkHttp, Alamofire, CFNetwork)

**Endpoints:**
- `POST /api/auth/login` - Authenticate and get tokens
- `POST /api/auth/refresh` - Exchange refresh token for new tokens
- `POST /api/auth/logout` - Clear refresh token (web)

## Testing Conventions

**Test Structure:**
- Mirror `app/` structure in `tests/` (e.g., `tests/routes/v1/test_tasks.py`)
- Use in-memory SQLite for fast, isolated tests
- Fixtures in `tests/conftest.py`

**Key Fixtures:**
- `async_engine`: In-memory SQLite engine
- `async_session`: Database session for tests
- `test_user`: Sample user with authentication
- `auth_headers`: Authorization headers for authenticated requests
- `test_client`: FastAPI TestClient with overridden dependencies

**Pattern:**
```python
async def test_create_task(test_client, auth_headers, test_org):
    response = test_client.post(
        f"/api/v1/tasks?org_id={test_org.id}",
        json={"summary": "Test task"},
        headers=auth_headers,
    )
    assert response.status_code == 201
```

## Development Workflow

1. **Model Changes:** Modify SQLModel in `app/models/`
2. **Generate Migration:** `uv run scripts/alembic_revision.py "description" --autogenerate`
3. **Review Migration:** Check autogenerated file in `alembic/versions/`
4. **Apply Migration:** `uv run alembic upgrade head`
5. **Update Logic:** Add/modify business logic in `app/logic/v1/`
6. **Update Routes:** Add/modify endpoints in `app/routes/v1/`
7. **Write Tests:** Add tests in `tests/`
8. **Run Tests:** `uv run pytest -v --cov=app`
9. **Format & Lint:** `uv run scripts/dev.py format && uv run scripts/dev.py lint`

## Important Notes

- **Always use async/await** - All database operations are async
- **Type hints required** - mypy strict mode enforced
- **Soft deletes only** - Use `deleted_at` field, not hard deletes (except system root role)
- **Organization-scoped data** - Most entities belong to an organization, verify membership
- **Audit trail** - Always set `created_by`, `last_modified_by` from authenticated user
- **Transaction boundaries** - Commit in logic layer, not routes
- **Schema validation** - Use Pydantic schemas for request/response, not raw models
- **Python 3.14+** - Uses modern Python features
- **uv for everything** - Don't use pip directly, use uv for package management

## API Versioning

All endpoints under `/api/v1/` for version 1:
- Organizations: `/api/v1/organizations`
- Projects: `/api/v1/projects`
- Tasks: `/api/v1/tasks`
- Teams: `/api/v1/teams`
- Features: `/api/v1/features`
- Sprints: `/api/v1/sprints`
- Deployment Environments: `/api/v1/deployment-envs`
- Documentation: `/api/v1/docs`

Authentication endpoints not versioned: `/api/auth/`

## Security

**Role-Based Access:**
- `SYSTEM` - System-level access
- `SYSTEM_ROOT` - Root system access
- `SYSTEM_ADMIN` - Admin privileges
- `SYSTEM_USER` - Standard user
- `SYSTEM_CLIENT` - Client application

**Permission Checks:**
Use functions from `app/logic/deps.py`:
- `check_system_root_role(user)` - Requires SYSTEM_ROOT
- `check_system_admin_role(user)` - Requires SYSTEM/SYSTEM_ROOT/SYSTEM_ADMIN
- `check_system_user_role(user)` - Requires SYSTEM_USER or higher
- `check_hard_delete_privileges(user)` - Requires SYSTEM or SYSTEM_ROOT
- `verify_organization_membership(org_id, user_id, db)` - Verify org access

**Initial Credentials (Local Dev):**
- Username: `root`
- Password: `P@ssword12`
