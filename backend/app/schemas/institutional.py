"""Pydantic schemas for Dimension 5: Institutional Integration (CWC, IMD, PDNA & CDRI)."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CWCStationData(BaseModel):
    station_code: str
    station_name: str
    river: str = "Bhagirathi"
    current_stage_m: float
    warning_level_m: float
    danger_level_m: float
    high_flood_level_m: float
    status: str = Field(..., description="NORMAL, WARNING, DANGER, CRITICAL")
    trend: str = Field(..., description="RISING, FALLING, STEADY")
    last_updated: datetime


class IMDDopplerScan(BaseModel):
    radar_station: str = "DWR_SURKANDA_DEVI"
    latitude: float = 30.407
    longitude: float = 78.285
    reflectivity_dbz: float
    radial_velocity_ms: float
    rain_rate_mm_hr: float
    convective_cell_detected: bool
    timestamp: datetime


class PDNADossierRequest(BaseModel):
    incident_name: str
    disaster_type: str = "Flash Flood & Landslide Surge"
    village_ids: List[str]
    assessor_name: str = "NDMA / District Disaster Management Officer"


class SectorLossSummary(BaseModel):
    sector_name: str
    damages_inr_lakhs: float
    losses_inr_lakhs: float
    total_need_inr_lakhs: float
    description: str


class PDNADossierResponse(BaseModel):
    dossier_id: str
    incident_name: str
    ndma_standard_compliant: bool = True
    assessor_name: str
    villages_assessed_count: int
    households_displaced: int
    sector_breakdown: List[SectorLossSummary]
    total_reconstruction_cost_inr_crores: float
    priority_early_recovery_actions: List[str]
    generated_at: datetime


class CDRIScoreSchema(BaseModel):
    village_id: str
    village_name: str
    overall_cdri_score: float = Field(..., ge=0.0, le=100.0)
    infrastructure_score: float
    social_vulnerability_score: float
    economic_coping_score: float
    institutional_readiness_score: float
    hazard_exposure_score: float
    resilience_tier: str = Field(..., description="TIER_1_ROBUST, TIER_2_MODERATE, TIER_3_VULNERABLE, TIER_4_CRITICAL")
