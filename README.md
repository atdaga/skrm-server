# Python Server

A modern Python web server built with FastAPI, featuring structured logging, comprehensive testing, and development best practices.

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


### Populate Database

Username: ***super***

Password: ***P@ssword12***
```
INSERT INTO k_principal (id,"scope",username,primary_email,primary_email_verified,primary_phone,primary_phone_verified,human,enabled,time_zone,name_prefix,first_name,middle_name,last_name,name_suffix,display_name,default_locale,system_role,meta,created,created_by,last_modified,last_modified_by) VALUES
	 ('00000000-0000-0000-0000-000000000000'::uuid,'global','super','super@global.scope',false,NULL,false,true,true,'UTC',NULL,'Super',NULL,'User',NULL,'Super User','en','system_user','{}','2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid);

INSERT INTO k_principal_identity (id,principal_id,"password",public_key,device_id,expires,details,created,created_by,last_modified,last_modified_by) VALUES
	 ('0199b6d7-a94f-75e9-a466-fa51620e7181'::uuid,'00000000-0000-0000-0000-000000000000'::uuid,'$2b$12$rdK6qPYTy0OEmjrHSlqsv.GSkqqi2gcJJyMIsMma.SeQS1HwqG002',NULL,NULL,NULL,'{}','2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid);

```

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

### API Endpoints

- `GET /` - Hello World endpoint
- `GET /health` - Health check endpoint

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
