import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health, users
from app.config import settings
from app.logging import get_logger, setup_logging

# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Use uvloop if available
if sys.platform != "win32":
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop for improved async performance")
    except ImportError:
        logger.warning("uvloop not available, using default asyncio loop")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting up application", app_name=settings.app_name)
    yield
    logger.info("Shutting down application")


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
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )
