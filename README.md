# sKrm Server

Backend API for the sKrm application built with FastAPI, featuring structured logging, comprehensive testing, and development best practices.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Async/Await**: Full async support for improved performance
- **Structured Logging**: Using structlog for better log management
- **Type Safety**: Full type hints with mypy validation
- **Code Quality**: Black formatting, isort, and ruff linting
- **Testing**: Comprehensive test suite with pytest
- **Configuration**: Pydantic-based settings management

## Quick Start

### Prerequisites

Install the following before proceeding:

- **Python 3.14+** - [Download](https://www.python.org/downloads/)
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Fast Python package installer and resolver
- **[PostgreSQL](https://www.postgresql.org/download/)** - Database server

### Installation

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your database credentials and other settings.

### Database Setup

1. **Create database and database user:**

   ```sql
   postgres=# CREATE DATABASE skrm_local;
   postgres=# CREATE USER skrm_user WITH ENCRYPTED PASSWORD 'P@ssword12';
   postgres=# GRANT ALL PRIVILEGES ON DATABASE skrm_local TO skrm_user;
   postgres=# \c skrm_local;
   postgres=# GRANT ALL PRIVILEGES ON SCHEMA public TO skrm_user;
   postgres=# \q
   ```

2. **Run database migrations:**

   ```bash
   uv run alembic upgrade head
   ```

   > See [Database Migrations](#database-migrations) for detailed migration information.

   **Initial Root User Credentials for local (from migration):**
   - Username: `root`
   - Password: `P@ssword12`

### Start the Server

```bash
# Using the development script
uv run scripts/dev.py serve

# Or directly with uvicorn
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for interactive API documentation.

---

## Development

You can either use the provided development scripts or run commands directly with uv:

### Using development scripts

```bash
# Start development server
uv run scripts/dev.py serve

# Run tests
uv run scripts/dev.py test

# Format code
uv run scripts/dev.py format

# Run linting
uv run scripts/dev.py lint

# Clean up test results and build artifacts
uv run scripts/dev.py clean

# Remove all generated files and caches (reset to git state)
uv run scripts/dev.py pristine
```

### Using uv directly

```bash
# Start development server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest -v --cov=app --cov-report=term-missing

# Format code
uv run black .
uv run isort .
uv run ruff check --fix .

# Run linting
uv run ruff check .
uv run black --check .
uv run isort --check-only .
uv run mypy app

# Clean up test results and build artifacts
rm -rf .pytest_cache .coverage dist build

# Remove all generated files and caches (reset to git state)
rm -rf .pytest_cache .coverage dist build .mypy_cache .ruff_cache .venv
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### Using Docker Compose

Run the application in a Docker container while connecting to your local PostgreSQL:

```bash
# Ensure .env exists with your database credentials
cp .env.example .env  # if not already done

# Start the application
docker compose up

# Start in background (detached mode)
docker compose up -d

# View logs
docker compose logs -f

# Stop the application
docker compose down

# Rebuild after code changes
docker compose up --build
```

**Note:** The container connects to your local PostgreSQL via `host.docker.internal`. Ensure your PostgreSQL is configured to accept connections from Docker (check `pg_hba.conf` if needed).

**Running migrations:** Migrations are not run automatically. Run them separately:

```bash
uv run alembic upgrade head
```

### Dependency Management

Always check if your lock file is up-to-date.

```bash
uv lock --check
```

If you manually modify dependencies in `pyproject.toml`, you need to run:

```bash
uv lock
```

This command updates the `uv.lock` file to reflect your changes. The lock file contains exact versions and dependency resolution for reproducible installations across different environments. This ensures all developers and deployment environments use identical dependency versions.

## Update Package Versions Flow

### Why Upgrade Package Dependencies?

Upgrading package dependencies in a software project is important for several key reasons:

- **Security fixes**: Newer package versions often include patches for known vulnerabilities, protecting your project from exploits. Staying updated prevents security risks and reduces the maintenance effort associated with emergency patches.

- **New features and improved APIs**: Upgrades frequently provide new functionalities and enhanced interfaces, enabling you to develop additional capabilities in your software.

- **Bug fixes and performance improvements**: Updated versions address bugs and often improve performance and efficiency, contributing to a more robust and faster software product.

- **Avoiding technical debt**: Regular updates prevent the accumulation of outdated dependencies that become increasingly difficult and risky to upgrade later, especially when multiple versions behind.

- **Maintain forward compatibility**: Keeping dependencies current ensures your environment continues to build and integrate smoothly over time, reducing the risk of breaking changes.

**Best practice**: Upgrade packages regularly during development cycles, test thoroughly before committing, and lock versions as you approach release. This strategy balances the benefits of updates early in development with stability at release time, helping you avoid falling behind on security and features while ensuring stable releases.

### Upgrade Workflow

1. **Upgrade dependency versions in lock file**

   ```bash
   uv lock --upgrade
   ```

   This updates uv.lock to the latest compatible versions but does not modify pyproject.toml or install packages.

2. **Install upgraded versions**

   ```bash
   uv sync
   ```

   This installs the upgraded versions specified in the updated uv.lock file.

3. **Test thoroughly**

   The exact command is in the Development section above.
   Run the full test suite to ensure the upgraded dependencies don't break anything.

4. **Update pyproject.toml with tested versions**

   After confirming everything works, update the version constraints in pyproject.toml to match the successfully tested versions. Use this command to see installed versions:

   ```bash
   uv pip list
   ```

   This approach ensures you only commit version constraints that have been tested, avoiding the need to revert changes if something breaks.

5. **Commit both pyproject.toml and uv.lock**

   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Update dependencies"
   ```

## Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Alembic provides version control for your database schema, allowing you to track changes, apply updates, and rollback modifications safely.

### What Are Migrations?

Database migrations are scripts that describe changes to your database schema (tables, columns, indexes, constraints, etc.). They allow you to:

- **Version Control**: Track schema changes alongside your code
- **Reproducibility**: Apply the same schema changes across different environments (dev, staging, production)
- **Rollback**: Safely undo changes if needed
- **Collaboration**: Team members can apply schema changes consistently
- **Deployment**: Automate schema updates during deployments

Each migration file contains:

- **Upgrade function**: Applies the changes (e.g., creates a table, adds a column)
- **Downgrade function**: Reverses the changes (e.g., drops a table, removes a column)

### Configuration

Alembic is configured to use separate environment variables from your application settings, allowing independent configuration for migrations.

#### Environment Variables

Set these in your `.env` file or export them in your shell:

**Option 1: Full Database URL**

```bash
ALEMBIC_DATABASE_URL=postgresql+asyncpg://skrm_user:P@ssword12@127.0.0.1:5432/skrm_local
```

**Option 2: Individual Components**

```bash
ALEMBIC_DB_HOST=127.0.0.1
ALEMBIC_DB_PORT=5432
ALEMBIC_DB_NAME=skrm_local
ALEMBIC_DB_USER=skrm_user
ALEMBIC_DB_PASSWORD=P@ssword12
```

#### Environment-Specific Configuration

For different environments, use environment-specific `.env` files or set variables directly:

#### Validating Configuration

Before running migrations, validate your configuration.

**1. Check current database connection:**

```bash
uv run alembic current
```

This will show the current migration version if connected successfully, or an error if the database is unreachable.

**2. Test connection without running migrations:**

```bash
# This will attempt to connect and show any connection errors
uv run python -c "from alembic import context; from alembic.config import Config; config = Config('alembic.ini'); print('Config loaded successfully')"
```

**3. View migration history:**

```bash
uv run alembic history
```

This shows all available migrations without connecting to the database.

### Performing Migrations

#### Creating Migrations

**Automatic Migration Generation (Recommended)**

Alembic can automatically detect changes to your SQLModel models and generate migration files. You don't need to specify what changed - Alembic compares your models with the current database schema and detects all differences automatically.

**Workflow:**

1. **Modify or add models** in `app/models/` (e.g., add a new column, create a new table, change a data type)

2. **Run autogenerate** with a descriptive name for the migration:

   ```bash
   # Using the helper script (uses timestamp-based naming)
   uv run scripts/alembic_revision.py "descriptive_name" --autogenerate
   
   # Or manually (Alembic uses timestamp-based naming by default)
   uv run alembic revision --autogenerate -m "descriptive_name"
   ```

3. **Alembic automatically detects all changes** between your models and the database schema:
   - New tables
   - New columns
   - Modified columns (type changes, nullable changes, etc.)
   - Dropped columns
   - New indexes
   - New constraints
   - Foreign key relationships

4. **Review the generated migration file** in `alembic/versions/` to ensure it's correct

5. **Apply the migration** when ready

**Example:**

```bash
# You added a new 'last_login' column to KPrincipal model
# Just run:
uv run scripts/alembic_revision.py "add_last_login_to_principal" --autogenerate

# Alembic will create a file like: 20241115_143022_add_last_login_to_principal.py
# (timestamp format: YYYYMMDD_HHMMSS_description)

# Alembic will automatically detect:
# - The new 'last_login' column
# - Its data type (DateTime)
# - Whether it's nullable
# - Any default values
# And generate the appropriate migration code
```

**Note:** The migration name you provide is just a label for the migration file - it doesn't need to match every change exactly. Alembic automatically detects and includes all model changes in the migration.

**Manual Migration Creation**

For custom migrations (DDL/DML that can't be auto-detected):

```bash
# Using helper script
uv run scripts/alembic_revision.py "custom_data_migration"

# Or manually
uv run alembic revision -m "custom_data_migration"
```

This creates an empty migration file that you can edit manually.

#### Reviewing Generated Migrations

**Always review autogenerated migrations before applying them:**

1. Open the generated file in `alembic/versions/` (e.g., `20241115_143022_add_user_email_index.py`)
2. Check the `upgrade()` function to ensure it creates the correct schema
3. Verify the `downgrade()` function correctly reverses the changes
4. Look for any issues:
   - Missing indexes or constraints
   - Incorrect data types
   - Missing foreign key relationships
   - Column defaults or nullable settings

**Example migration file:**

```python
"""add_user_email_index

Revision ID: abc123
Revises: def456
Create Date: 2024-11-15 14:30:22.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'abc123'
down_revision: Union[str, None] = 'def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_index('ix_k_principal_email', 'k_principal', ['primary_email'], unique=True)

def downgrade() -> None:
    op.drop_index('ix_k_principal_email', table_name='k_principal')
```

#### Applying Migrations

**Apply all pending migrations:**

```bash
uv run alembic upgrade head
```

**Apply migrations one at a time:**

```bash
uv run alembic upgrade +1
```

**Apply migrations to a specific revision:**

```bash
uv run alembic upgrade abc123
```

**Check current migration version:**

```bash
uv run alembic current
```

#### Rolling Back Migrations

**Rollback one migration:**

```bash
uv run alembic downgrade -1
```

**Rollback to a specific revision:**

```bash
uv run alembic downgrade abc123
```

**Rollback all migrations:**

```bash
uv run alembic downgrade base
```

⚠️ **Warning**: Rolling back migrations can cause data loss. Always backup your database before rolling back in production.

### Automatic Migration Workflow

#### After Model Changes/Additions

When you add or modify SQLModel models, Alembic automatically detects all changes:

1. **Modify your model** in `app/models/` (e.g., `app/models/k_user.py`)
   - Add new columns
   - Change column types
   - Add new tables
   - Modify relationships
   - Add indexes or constraints

2. **Generate migration automatically** - Alembic detects all changes:

   ```bash
   uv run scripts/alembic_revision.py "descriptive_name" --autogenerate
   ```

   **You don't need to specify what changed** - Alembic compares your models with the database schema and automatically includes all differences in the migration.

3. **Review the generated migration** in `alembic/versions/`
   - Check that all expected changes are included
   - Verify column types, constraints, and relationships are correct
   - Look for any missing changes that Alembic might have missed

4. **Test the migration:**

   ```bash
   # Apply to development database
   uv run alembic upgrade head
   
   # Verify the changes
   uv run alembic current
   ```

5. **Test rollback (optional but recommended):**

   ```bash
   uv run alembic downgrade -1
   uv run alembic upgrade head
   ```

6. **Commit both model and migration files** together

#### Best Practices

- **One logical change per migration**: Don't mix unrelated schema changes
- **Test migrations locally first**: Always test on development/staging before production
- **Review autogenerated migrations**: Alembic may miss some changes or generate incorrect code
- **Keep migrations small**: Easier to review, test, and rollback
- **Never edit applied migrations**: Create a new migration to fix issues
- **Use descriptive names**: Migration names should clearly describe what they do

### Custom DDL/DML Migrations

Sometimes you need to perform operations that Alembic can't autogenerate:

- **Data migrations**: Transform existing data
- **Custom SQL**: Complex operations, stored procedures, functions
- **Index management**: Partial indexes, expression indexes
- **Schema changes**: Creating schemas, setting permissions

#### Adding Custom DDL (Data Definition Language)

**Example: Creating a custom index**

```python
"""add_partial_index_active_users

Revision ID: xyz789
Revises: abc123
Create Date: 2024-01-20 14:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'xyz789'
down_revision: Union[str, None] = 'abc123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create a partial index (only indexes active users)
    op.execute("""
        CREATE INDEX ix_k_principal_active_email 
        ON k_principal(primary_email) 
        WHERE enabled = true
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_k_principal_active_email")
```

**Example: Adding a check constraint**

```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE k_task 
        ADD CONSTRAINT check_positive_estimate 
        CHECK (estimate_hours > 0)
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE k_task DROP CONSTRAINT check_positive_estimate")
```

#### Adding Custom DML (Data Manipulation Language)

**Example: Data migration**

```python
"""migrate_legacy_user_data

Revision ID: data001
Revises: xyz789
Create Date: 2024-01-25 09:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'data001'
down_revision: Union[str, None] = 'xyz789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Update existing data
    op.execute("""
        UPDATE k_principal 
        SET display_name = first_name || ' ' || last_name 
        WHERE display_name IS NULL
    """)
    
    # Insert default data
    op.execute("""
        INSERT INTO k_organization (id, name, created, created_by)
        VALUES ('00000000-0000-0000-0000-000000000000', 'Default Organization', NOW(), '00000000-0000-0000-0000-000000000000')
        ON CONFLICT (id) DO NOTHING
    """)

def downgrade() -> None:
    # Reverse data changes
    op.execute("UPDATE k_principal SET display_name = NULL WHERE display_name = first_name || ' ' || last_name")
    op.execute("DELETE FROM k_organization WHERE id = '00000000-0000-0000-0000-000000000000'")
```

**Example: Using connection for complex operations**

```python
def upgrade() -> None:
    conn = op.get_bind()
    
    # Use connection for complex queries
    result = conn.execute(sa.text("SELECT id, email FROM k_principal WHERE email IS NOT NULL"))
    
    for row in result:
        # Process each row
        conn.execute(
            sa.text("UPDATE k_principal SET primary_email = :email WHERE id = :id"),
            {"email": row.email.lower(), "id": row.id}
        )

def downgrade() -> None:
    # Reverse the changes
    pass  # Or implement reverse logic
```

#### Using Alembic Operations

Alembic provides helper functions for common operations:

```python
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Create table
    op.create_table(
        'k_audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add column
    op.add_column('k_principal', sa.Column('last_login', sa.DateTime(), nullable=True))
    
    # Create index
    op.create_index('ix_k_principal_last_login', 'k_principal', ['last_login'])
    
    # Add foreign key
    op.create_foreign_key(
        'fk_task_principal', 
        'k_task', 
        'k_principal', 
        ['owner_id'], 
        ['id']
    )
    
    # Alter column
    op.alter_column('k_task', 'status',
                    existing_type=sa.String(20),
                    nullable=False)

def downgrade() -> None:
    op.drop_constraint('fk_task_principal', 'k_task', type_='foreignkey')
    op.drop_index('ix_k_principal_last_login', table_name='k_principal')
    op.drop_column('k_principal', 'last_login')
    op.drop_table('k_audit_log')
```

### Common Migration Commands

```bash
# Show current migration version
uv run alembic current

# Show migration history
uv run alembic history

# Show pending migrations
uv run alembic history --verbose

# Create new migration (autogenerate)
uv run scripts/alembic_revision.py "migration_name" --autogenerate

# Create new migration (manual)
uv run scripts/alembic_revision.py "migration_name"

# Apply all pending migrations
uv run alembic upgrade head

# Apply one migration
uv run alembic upgrade +1

# Rollback one migration
uv run alembic downgrade -1

# Rollback all migrations
uv run alembic downgrade base

# Show SQL that would be executed (without applying)
uv run alembic upgrade head --sql
```

### Troubleshooting

**Connection Errors:**

- Verify database is running: `psql -h 127.0.0.1 -U skrm_user -d skrm_local`
- Check environment variables are set correctly
- Verify database credentials match your `.env` file

**Migration Conflicts:**

- If multiple developers create migrations simultaneously, you may need to merge them
- Use `alembic merge` to combine multiple migration branches

**Autogenerate Issues:**

- Alembic may not detect all changes (especially complex relationships)
- Always review autogenerated migrations
- Manually add missing operations if needed

**Rollback Failures:**

- Some migrations cannot be automatically reversed
- Implement custom downgrade logic for complex migrations
- Test rollbacks in development before production

## Authentication & Refresh Tokens

The API implements a dual-strategy refresh token system that supports both web SPAs and mobile applications with optimal security for each platform.

### Overview

**Refresh Token Strategy:**

- **Web Clients (SPAs)**: Refresh tokens are stored in HTTP-only cookies (XSS protection)
- **Mobile Clients (iOS/Android)**: Refresh tokens are returned in response body (stored securely in Keychain/Keystore)

**Client Detection:**

- Preferred: `X-Client-Type: mobile` header
- Fallback: User-Agent patterns (OkHttp, Alamofire, CFNetwork)

### Security Features

1. **HTTP-only Cookies**: Not accessible to JavaScript (XSS protection)
2. **SameSite=Strict**: CSRF protection for web clients
3. **Secure Flag**: Conditional based on environment
   - `False` in development (allows HTTP)
   - `True` in production (HTTPS only)
4. **Token Rotation**: Both access and refresh tokens are rotated on refresh
5. **Path Restriction**: Cookies only sent to `/api/auth` endpoints

### Cookie Configuration

The `cookie_secure` setting automatically adjusts based on the `debug` flag:

- When `debug=True`: `cookie_secure` is set to `False` (allows HTTP cookies for local development)
- When `debug=False`: `cookie_secure` defaults to `True` (requires HTTPS)

### Usage Examples

#### Web SPA (JavaScript)

**Login:**

```javascript
// Login - cookie set automatically
const formData = new FormData();
formData.append('username', 'user@example.com');
formData.append('password', 'password123');

const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  credentials: 'include', // Important: sends/receives cookies
  body: formData
});

const { access_token, token_type } = await response.json();
// Refresh token is in HTTP-only cookie, not accessible to JavaScript
// Store access_token in memory or sessionStorage
```

**Refresh Token:**

```javascript
// Refresh - cookie sent automatically
const refreshResponse = await fetch('http://localhost:8000/api/auth/refresh', {
  method: 'POST',
  credentials: 'include', // Cookie sent automatically
});

const { access_token } = await refreshResponse.json();
// New refresh token cookie is set automatically
```

**Logout:**

```javascript
// Logout - clears refresh token cookie
await fetch('http://localhost:8000/api/auth/logout', {
  method: 'POST',
  credentials: 'include',
});
```

**Using Access Token:**

```javascript
// Include access token in Authorization header for API requests
const apiResponse = await fetch('http://localhost:8000/api/v1/some-endpoint', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  credentials: 'include'
});
```

#### Mobile iOS (Swift)

**Login:**

```swift
import Foundation

// Login - include header to identify as mobile client
var request = URLRequest(url: URL(string: "http://localhost:8000/api/auth/login")!)
request.httpMethod = "POST"
request.setValue("mobile", forHTTPHeaderField: "X-Client-Type")
request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

let body = "username=user@example.com&password=password123"
request.httpBody = body.data(using: .utf8)

let (data, _) = try await URLSession.shared.data(for: request)
let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)

// Store refresh_token securely in Keychain
KeychainHelper.store(tokenResponse.refresh_token, forKey: "refresh_token")
// Store access_token in memory
```

**Refresh Token:**

```swift
// Refresh - send token in request body
var refreshRequest = URLRequest(url: URL(string: "http://localhost:8000/api/auth/refresh")!)
refreshRequest.httpMethod = "POST"
refreshRequest.setValue("mobile", forHTTPHeaderField: "X-Client-Type")
refreshRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")

let storedToken = KeychainHelper.retrieve(forKey: "refresh_token")
let refreshBody = ["refresh_token": storedToken]
refreshRequest.httpBody = try JSONEncoder().encode(refreshBody)

let (data, _) = try await URLSession.shared.data(for: refreshRequest)
let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)

// Update stored tokens
KeychainHelper.store(tokenResponse.refresh_token, forKey: "refresh_token")
```

**Token Response Model:**

```swift
struct TokenResponse: Codable {
    let access_token: String
    let token_type: String
    let refresh_token: String
}
```

#### Mobile Android (Kotlin)

**Login:**

```kotlin
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody

// Login - include header to identify as mobile client
val client = OkHttpClient()
val formBody = FormBody.Builder()
    .add("username", "user@example.com")
    .add("password", "password123")
    .build()

val request = Request.Builder()
    .url("http://localhost:8000/api/auth/login")
    .addHeader("X-Client-Type", "mobile")
    .post(formBody)
    .build()

val response = client.newCall(request).execute()
val tokenResponse = JSONObject(response.body?.string() ?: "")

// Store refresh_token securely in EncryptedSharedPreferences or Keystore
val refreshToken = tokenResponse.getString("refresh_token")
SecureStorage.store("refresh_token", refreshToken)
```

**Refresh Token:**

```kotlin
// Refresh - send token in request body
val refreshToken = SecureStorage.retrieve("refresh_token")
val jsonBody = JSONObject().apply {
    put("refresh_token", refreshToken)
}.toString().toRequestBody("application/json".toMediaType())

val refreshRequest = Request.Builder()
    .url("http://localhost:8000/api/auth/refresh")
    .addHeader("X-Client-Type", "mobile")
    .post(jsonBody)
    .build()

val refreshResponse = client.newCall(refreshRequest).execute()
val newTokenResponse = JSONObject(refreshResponse.body?.string() ?: "")

// Update stored tokens
SecureStorage.store("refresh_token", newTokenResponse.getString("refresh_token"))
```

### API Endpoints

**Authentication:**

- `POST /api/auth/login` - Authenticate user and get tokens
- `POST /api/auth/refresh` - Exchange refresh token for new tokens
- `POST /api/auth/logout` - Clear refresh token cookie (web clients)

**Request/Response Format:**

**Login (Web):**

```bash
# Request
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=password123

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": null  # null for web clients (token in cookie)
}
# Set-Cookie: refresh_token=eyJ...; HttpOnly; SameSite=Strict; Path=/api/auth
```

**Login (Mobile):**

```bash
# Request
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded
X-Client-Type: mobile

username=user@example.com&password=password123

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": "eyJ..."  # Included in body for mobile
}
```

**Refresh (Web):**

```bash
# Request
POST /api/auth/refresh
Cookie: refresh_token=eyJ...

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": null  # null (new token in cookie)
}
# Set-Cookie: refresh_token=eyJ...; HttpOnly; SameSite=Strict; Path=/api/auth
```

**Refresh (Mobile):**

```bash
# Request
POST /api/auth/refresh
Content-Type: application/json
X-Client-Type: mobile

{"refresh_token": "eyJ..."}

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": "eyJ..."  # New refresh token in body
}
```

## Project Structure

```text
├── alembic/                    # Database migrations
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic environment configuration
├── app/                        # Main application code
│   ├── core/                   # Core functionality
│   │   ├── auth.py             # Authentication utilities
│   │   ├── context.py          # Request context management
│   │   ├── db/                 # Database connection and session management
│   │   ├── exceptions/         # Custom exception classes
│   │   ├── fido2_server.py     # FIDO2 authentication server
│   │   ├── logging.py          # Logging configuration
│   │   ├── middleware.py       # FastAPI middleware
│   │   └── weaviate/           # Weaviate vector database integration
│   ├── logic/                  # Business logic layer
│   │   ├── auth.py             # Authentication logic
│   │   ├── deps.py             # Dependency injection functions
│   │   └── v1/                 # API v1 business logic
│   │       ├── organizations.py
│   │       ├── projects.py
│   │       ├── tasks.py
│   │       └── ...             # Other domain logic modules
│   ├── models/                 # SQLModel database models
│   │   ├── k_principal.py      # Principal/user model
│   │   ├── k_organization.py   # Organization model
│   │   ├── k_project.py        # Project model
│   │   ├── k_task.py           # Task model
│   │   └── ...                 # Other domain models
│   ├── routes/                 # API route handlers
│   │   ├── auth.py             # Authentication routes
│   │   ├── health.py           # Health check endpoint
│   │   └── v1/                 # API v1 routes
│   │       ├── organizations.py
│   │       ├── projects.py
│   │       ├── tasks.py
│   │       └── ...             # Other domain route modules
│   ├── schemas/                # Pydantic schemas for request/response
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── ...                 # Other domain schemas
│   ├── config.py               # Application configuration
│   └── main.py                 # FastAPI application entry point
├── tests/                      # Test suite
│   ├── core/                   # Core functionality tests
│   ├── logic/                  # Business logic tests
│   ├── models/                 # Model tests
│   ├── routes/                 # Route handler tests
│   └── conftest.py             # Pytest configuration and fixtures
├── scripts/                     # Utility scripts
│   ├── alembic_revision.py     # Alembic migration helper
│   └── dev.py                  # Development workflow scripts
├── alembic.ini                 # Alembic configuration
├── pyproject.toml               # Project configuration and dependencies
└── uv.lock                      # Dependency lock file
```
