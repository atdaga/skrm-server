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

### Installation

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
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
