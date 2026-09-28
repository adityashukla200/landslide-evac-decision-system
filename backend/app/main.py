"""FastAPI application entrypoint for the Early Warning System."""

import time
import logging
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis

from backend.app.core.config import settings
from backend.app.db.session import get_db, engine, Base
from backend.app.api.router import api_router
from backend.app.services.ingestion.scheduler import ingestion_scheduler
from ml.data.loaders import load_feature_table

logger = logging.getLogger(__name__)

# Ensure tables are created
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown procedures.
    
    Loads pre-computed feature tables and artifacts once into memory at server start,
    logging load times, and starts background telemetry ingestion tasks.
    """
    logger.info("[Startup] Initiating application startup...")
    t0 = time.perf_counter()

    # Preload feature table parquet into memory once
    try:
        logger.info("[Startup] Preloading processed feature table parquet into app.state...")
        app.state.feature_table = load_feature_table()
        load_duration = time.perf_counter() - t0
        logger.info(
            f"[Startup] Successfully loaded feature table ({len(app.state.feature_table):,} rows) "
            f"in {load_duration:.3f}s."
        )
    except Exception as exc:
        logger.error(f"[Startup] Failed to preload feature table: {exc}", exc_info=True)
        app.state.feature_table = None

    # Start non-blocking background ingestion scheduler
    ingestion_scheduler.start()

    yield

    # Clean shutdown
    logger.info("[Shutdown] Stopping background ingestion scheduler...")
    ingestion_scheduler.stop()
    logger.info("[Shutdown] Application cleanup complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Village/ward-level Early Warning System for Flash Floods and Landslides (MHA/NDRF PS26192)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for local Vite dev server and production clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply Rate Limiting (180 requests/min per IP)
from backend.app.core.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=180)

# Mount API v1 router
app.include_router(api_router)

# Mount evacuation assessment directly under /api/assess/{village_id}
from backend.app.api.endpoints.evacuation import router as evacuation_router
app.include_router(evacuation_router, prefix="/api")

# Mount alerting directly under /api (alerts, reports, drills)
from backend.app.api.endpoints.alerting import router as alerting_router
app.include_router(alerting_router, prefix="/api")


@app.get("/", tags=["Root"])
def root() -> Dict[str, Any]:
    """Root status endpoint."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Health check endpoint verifying database and Redis connectivity."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unreachable: {str(exc)}"

    redis_status = "offline_fallback"
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        if r.ping():
            redis_status = "connected"
    except Exception:
        redis_status = "offline_fallback"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "database_type": "postgres" if settings.is_postgres else "sqlite",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }
