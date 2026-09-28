"""Data status and telemetry endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, status
from backend.app.services.ingestion.manager import data_manager
from backend.app.services.ingestion.scheduler import ingestion_scheduler

router = APIRouter(prefix="/data", tags=["Data Sources"])


@router.get("/status", status_code=status.HTTP_200_OK)
def get_data_sources_status() -> Dict[str, Any]:
    """Return operational state (LIVE/CACHED/SIMULATED), last fetch time, and latency per source."""
    return data_manager.get_source_status()


@router.post("/refresh", status_code=status.HTTP_200_OK)
def trigger_data_refresh() -> Dict[str, Any]:
    """Manually trigger a telemetry ingestion refresh cycle across all seeded villages."""
    records_written = ingestion_scheduler.ingest_once()
    return {
        "status": "success",
        "records_written": records_written,
        "data_status": data_manager.get_source_status(),
    }
