# Python Server

A modern Python web server built with FastAPI, featuring structured logging, comprehensive testing, and development best practices.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Async/Await**: Full async support with uvloop for improved performance
- **Structured Logging**: Using structlog for better log management
- **Type Safety**: Full type hints with mypy validation
- **Code Quality**: Black formatting, isort, and ruff linting
- **Testing**: Comprehensive test suite with pytest
- **Configuration**: Pydantic-based settings management

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry

### Installation

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env
```

### Development

```bash
# Start development server
python scripts/dev.py serve

# Run tests
python scripts/dev.py test

# Format code
python scripts/dev.py format

# Run linting
python scripts/dev.py lint
```

### API Endpoints

- `GET /` - Hello World endpoint
- `GET /health` - Health check endpoint

## Project Structure

```
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