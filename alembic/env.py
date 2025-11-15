import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context

# Import all models to register them with SQLModel metadata
# This ensures Alembic can detect all tables
from app.models import *  # noqa: F401, F403

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url() -> str:
    """Get database URL from environment variable or use default."""
    import os

    # Check for ALEMBIC_DATABASE_URL environment variable first
    url = os.getenv("ALEMBIC_DATABASE_URL")

    if url:
        return url

    # Fallback to constructing from individual environment variables
    db_host = os.getenv("ALEMBIC_DB_HOST", "127.0.0.1")
    db_port = os.getenv("ALEMBIC_DB_PORT", "5432")
    db_name = os.getenv("ALEMBIC_DB_NAME", "skrm_local")
    db_user = os.getenv("ALEMBIC_DB_USER", "skrm_user")
    db_password = os.getenv("ALEMBIC_DB_PASSWORD", "P@ssword12")

    # Use asyncpg driver for async migrations
    # URL encode password to handle special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(db_password)

    return f"postgresql+asyncpg://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Patch SQLAlchemy's enum creation to check if enum types exist first
    # This prevents errors when enum types already exist in the database
    from sqlalchemy.dialects.postgresql import ENUM

    # Store original _on_table_create method
    original_on_table_create = ENUM._on_table_create

    def patched_on_table_create(self, target, bind, **kw):
        """Patched version that uses checkfirst=True."""
        # Ensure checkfirst=True is set
        kw['checkfirst'] = True
        return original_on_table_create(self, target, bind, **kw)

    # Temporarily patch the method
    ENUM._on_table_create = patched_on_table_create

    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()
    finally:
        # Restore original method
        ENUM._on_table_create = original_on_table_create


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    import sys

    configuration = config.get_section(config.config_ini_section, {})
    database_url = get_url()
    configuration["sqlalchemy.url"] = database_url

    try:
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

        await connectable.dispose()
    except Exception as e:
        # Provide helpful error message for connection issues
        import os
        if "nodename nor servname provided" in str(e) or "could not translate host name" in str(e).lower():
            print("\n❌ Database connection error: Unable to resolve database hostname.", file=sys.stderr)
            print("\nPossible causes:", file=sys.stderr)
            print("  1. Database server is not running", file=sys.stderr)
            print("  2. Environment variables are not set correctly", file=sys.stderr)
            print("  3. Database hostname is incorrect", file=sys.stderr)
            print("\nCurrent configuration:", file=sys.stderr)
            print(f"  ALEMBIC_DATABASE_URL: {os.getenv('ALEMBIC_DATABASE_URL', 'not set')}", file=sys.stderr)
            print(f"  ALEMBIC_DB_HOST: {os.getenv('ALEMBIC_DB_HOST', '127.0.0.1 (default)')}", file=sys.stderr)
            print(f"  Database URL: {database_url.split('@')[0]}@***", file=sys.stderr)
            print("\nTo fix:", file=sys.stderr)
            print("  1. Set ALEMBIC_DATABASE_URL in your .env file or environment", file=sys.stderr)
            print("  2. Ensure PostgreSQL is running", file=sys.stderr)
            print("  3. Verify database connection details", file=sys.stderr)
        raise


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
