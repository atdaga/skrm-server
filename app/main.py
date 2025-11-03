import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .core.db.database import cleanup_database, create_all_tables, initialize_database
from .core.logging import get_logger, setup_logging
from .routes import auth, health, v1

# Setup logging first
setup_logging()
logger = get_logger(__name__)


# Use uvloop if available
if sys.platform != "win32":
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop for improved async performance")
    except ImportError:  # pragma: no cover
        logger.warning("uvloop not available, using default asyncio loop")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting up application", app_name=settings.app_name)

    # Initialize database and create tables
    try:
        logger.debug("Initializing database")
        initialize_database()
        logger.debug("Database initialized successfully")
        logger.debug("Creating all tables")
        await create_all_tables()
        logger.debug("Tables created successfully")
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    yield

    logger.info("Shutting down application")

    # Cleanup database connections
    try:
        logger.debug("Cleaning up database connections")
        await cleanup_database()
        logger.debug("Database cleanup completed successfully")
    except Exception as e:
        logger.error("Error during database cleanup", error=str(e))


app = FastAPI(
    title=settings.app_name,
    description="A modern Python web server built with FastAPI",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(v1.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.debug,
    )
