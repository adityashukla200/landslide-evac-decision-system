"""Pydantic schemas for Satellite Remote Sensing and Nowcast ingestion."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SatelliteLayerItem(BaseModel):
    """Satellite layer summary metadata."""

    source: str = Field(..., description="SENTINEL_1, SENTINEL_2, NASA_GPM, INSAT_3D")
    product_name: str
    acquisition_time: datetime
    resolution_meters: int
    coverage_area: str
    metrics: Dict[str, Any]
    geojson_url: Optional[str] = None
    raster_tile_url: Optional[str] = None


class SatelliteNowcastResponse(BaseModel):
    """Live nowcasting and satellite anomaly summary for a village."""

    village_id: str
    village_name: str
    insat_cloud_cooling_rate_k_15m: float = Field(..., description="Cloud-top brightness temperature rate of change (K/15min). < -15 indicates cloudburst")
    insat_cloudburst_probability: float = Field(..., ge=0.0, le=1.0)
    gpm_rain_rate_mm_h: float = Field(..., ge=0.0, description="NASA GPM IMERG instantaneous rain rate")
    gpm_3h_accumulation_mm: float = Field(..., ge=0.0)
    sentinel1_coherence_loss: float = Field(..., ge=0.0, le=1.0, description="InSAR coherence loss indicating surface deformation or vegetation loss")
    sentinel1_displacement_rate_mm_yr: float = Field(..., description="Estimated slope creep velocity (mm/year)")
    sentinel2_mndwi_surface_water_ha: float = Field(..., ge=0.0, description="Surface water extent detected in sub-basin (hectares)")
    risk_boost_factor: float = Field(..., ge=-0.5, le=0.5, description="Net calibrated threat boost added to model risk")
    threat_level: str = Field(..., description="CRITICAL, HIGH, ELEVATED, NORMAL")
    updated_at: datetime


class RiskFusionRequest(BaseModel):
    """Request to trigger multi-source satellite and ground telemetry risk fusion."""

    village_id: Optional[str] = None
    apply_to_all_villages: bool = True
