# Multi-stage Dockerfile for AWS ECS deployment
#
# Build with docker buildx (recommended):
#   docker buildx build --platform linux/amd64 -t python-server:latest .
#
# For AWS ECS, build and push to ECR:
#   docker buildx build --platform linux/amd64 -t <account-id>.dkr.ecr.<region>.amazonaws.com/python-server:<tag> .
#   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/python-server:<tag>
#
# Stage 1: Builder - Install dependencies using uv
FROM python:3.14-slim AS builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary from official uv Docker image
# This is more reliable than installing via script and works across architectures
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual environment (without installing the local package)
# --frozen ensures we use exact versions from uv.lock
# --no-install-project skips building/installing the local package (we'll copy app code later)
# --no-group excludes dev, test, and lint dependency groups (production only)
RUN uv sync --frozen --no-install-project --no-group dev --no-group test --no-group lint

# Stage 2: Runtime - Minimal production image
FROM python:3.14-slim AS runtime

# Install runtime system dependencies (if any are needed)
# Most Python packages should work with slim, but some may need additional libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
# TODO: Remove this once we have a proper migration system
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Make sure we use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port 8000
EXPOSE 8000

# Health check using the /health endpoint
# Uses Python's built-in urllib to avoid additional dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Run uvicorn in production mode
# Use environment variables for configuration flexibility
# Default to 4 workers, can be overridden via UVICORN_WORKERS env var
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-4}"]
