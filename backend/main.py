"""MetaFix - Plex Library Management Tool.

Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import close_db, init_db
from routers import artwork, autofix, edition, issues, plex, scan, schedules, settings
from services.scheduler_service import scheduler_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings_instance = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting MetaFix...")
    await init_db()
    logger.info("Database initialized")
    await scheduler_service.start()
    yield
    # Shutdown
    logger.info("Shutting down MetaFix...")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title="MetaFix",
    description="Plex library management tool for artwork and edition metadata",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime

    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Include routers
app.include_router(plex.router, prefix="/api/plex", tags=["Plex"])
app.include_router(scan.router, prefix="/api/scan", tags=["Scan"])
app.include_router(issues.router, prefix="/api/issues", tags=["Issues"])
app.include_router(artwork.router, prefix="/api/artwork", tags=["Artwork"])
app.include_router(edition.router, prefix="/api/edition", tags=["Edition"])
app.include_router(autofix.router, prefix="/api/autofix", tags=["AutoFix"])
app.include_router(schedules.router, prefix="/api/schedules", tags=["Schedules"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings_instance.debug,
    )
