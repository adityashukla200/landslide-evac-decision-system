"""API Endpoints for Dimension 5: Institutional Integration (CWC, IMD, PDNA & CDRI)."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends

from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import PDNADossier, VillageResilienceScore
from backend.app.schemas.institutional import (
    CWCStationData,
    IMDDopplerScan,
    PDNADossierRequest,
    PDNADossierResponse,
    CDRIScoreSchema,
)
from backend.app.services.institutional.cwc_imd import CWCStageConnector, IMDDopplerRadarConnector
from backend.app.services.institutional.pdna_generator import NDMAPDNAGenerator
from backend.app.services.institutional.resilience_index import CommunityResilienceIndexCalculator

router = APIRouter(prefix="/institutional", tags=["Institutional & Open Data Integration"])


@router.get("/cwc/stages", response_model=List[CWCStationData])
def get_cwc_river_stages():
    """Fetch live river stages, danger marks, and warning levels from Central Water Commission (CWC)."""
    return CWCStageConnector.get_all_stations()


@router.get("/imd/radar", response_model=IMDDopplerScan)
def get_imd_doppler_scan(station: str = "DWR_SURKANDA_DEVI"):
    """Fetch live reflectivity (dBZ) and rain rate from IMD Doppler Weather Radar."""
    return IMDDopplerRadarConnector.fetch_latest_scan(station=station)


@router.post("/pdna/generate", response_model=PDNADossierResponse)
def generate_pdna_dossier(request: PDNADossierRequest, db: Session = Depends(get_db)):
    """Generate official NDMA-compliant Post-Disaster Needs Assessment (PDNA) recovery report."""
    dossier = NDMAPDNAGenerator.generate_dossier(
        incident_name=request.incident_name,
        disaster_type=request.disaster_type,
        village_ids=request.village_ids,
        assessor_name=request.assessor_name,
    )

    # Persist in DB
    now = datetime.now(timezone.utc)
    db_rec = PDNADossier(
        id=dossier["dossier_id"],
        district="Uttarkashi",
        event_title=request.incident_name,
        start_time=now,
        end_time=now,
        impacted_villages_count=dossier["villages_assessed_count"],
        total_population_affected=dossier["households_displaced"] * 4,
        displaced_population=dossier["households_displaced"],
        infrastructure_damage_score=7.5,
        estimated_economic_loss_cr=dossier["total_reconstruction_cost_inr_crores"],
        verified_citizen_reports_count=12,
        executive_summary=f"Automated NDMA PDNA assessment for {request.incident_name}",
        dossier_json={
            **dossier,
            "generated_at": dossier["generated_at"].isoformat()
            if hasattr(dossier["generated_at"], "isoformat")
            else str(dossier["generated_at"]),
        },
    )
    db.add(db_rec)

    db.commit()


    return PDNADossierResponse(**dossier)


@router.get("/cdri/scores", response_model=List[CDRIScoreSchema])
def list_cdri_scores():
    """Retrieve Community Disaster Resilience Index (CDRI) for all monitored villages."""
    return CommunityResilienceIndexCalculator.calculate_all()


@router.get("/cdri/village/{village_id}", response_model=CDRIScoreSchema)
def get_village_cdri_score(village_id: str):
    """Retrieve CDRI resilience score and dimensional breakdown for a specific village."""
    return CommunityResilienceIndexCalculator.calculate_cdri(village_id)
