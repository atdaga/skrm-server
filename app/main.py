import asyncio
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import auth, health, users
from app.config import settings
from app.logging import get_logger, setup_logging
from app.core.db.database import create_all_tables, initialize_database, cleanup_database, cleanup_database_sync

# Setup logging first
setup_logging()
logger = get_logger(__name__)


def signal_handler(signum: int, _frame) -> None:
    """Handle shutdown signals for graceful cleanup."""
    logger.info(f"Received signal {signum}, cleaning up database connections")
    cleanup_database_sync()
    sys.exit(0)


# Register signal handlers for graceful shutdown
# signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
# signal.signal(signal.SIGTERM, signal_handler)   # Termination signal

# Use uvloop if available
if sys.platform != "win32":
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop for improved async performance")
    except ImportError:
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
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.debug,
    )
