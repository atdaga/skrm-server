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

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [PostgreSQL](https://www.postgresql.org/download/)

### Installation

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
```

### Database

```sql
postgres=# CREATE DATABASE skrm_local;
postgres=# CREATE USER skrm_user WITH ENCRYPTED PASSWORD 'P@ssword12';
postgres=# GRANT ALL PRIVILEGES ON DATABASE skrm_local TO skrm_user;
postgres=# \c skrm_local;
postgres=# GRANT ALL PRIVILEGES ON SCHEMA public TO skrm_user;
postgres=# \q
```

#### Initial User

Username: ***super***

Password: ***P@ssword12***

```sql
INSERT INTO k_principal (id,"scope",username,primary_email,primary_email_verified,primary_phone,primary_phone_verified,human,enabled,time_zone,name_prefix,first_name,middle_name,last_name,name_suffix,display_name,default_locale,system_role,meta,created,created_by,last_modified,last_modified_by) VALUES
 ('00000000-0000-0000-0000-000000000000'::uuid,'global','super','super@global.scope',false,NULL,false,true,true,'UTC',NULL,'Super',NULL,'User',NULL,'Super User','en','system_user','{}','2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid);

INSERT INTO k_principal_identity (id,principal_id,"password",public_key,device_id,expires,details,created,created_by,last_modified,last_modified_by) VALUES
 ('0199b6d7-a94f-75e9-a466-fa51620e7181'::uuid,'00000000-0000-0000-0000-000000000000'::uuid,'$2b$12$rdK6qPYTy0OEmjrHSlqsv.GSkqqi2gcJJyMIsMma.SeQS1HwqG002',NULL,NULL,NULL,'{}','2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid);
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

### Development

You can either use the provided development scripts or run commands directly with uv:

#### Using development scripts

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

#### Using uv directly

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

#### Dependency Management

Always check if your lock file is up-to-date.

```bash
uv lock --check
```

If you manually modify dependencies in `pyproject.toml`, you need to run:

```bash
uv lock
```

This command updates the `uv.lock` file to reflect your changes. The lock file contains exact versions and dependency resolution for reproducible installations across different environments. This ensures all developers and deployment environments use identical dependency versions.

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
  "refresh_token": ""  # Empty for web clients (in cookie)
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
  "refresh_token": ""  # Empty (new token in cookie)
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

## General API Endpoints

- `GET /` - Hello World endpoint
- `GET /health` - Health check endpoint

See the [Authentication & Refresh Tokens](#authentication--refresh-tokens) section above for authentication endpoints.

## Project Structure

```text
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration management
│   └── logging.py       # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_main.py     # API tests
├── scripts/
│   └── dev.py           # Development scripts
└── pyproject.toml       # Project configuration
```
