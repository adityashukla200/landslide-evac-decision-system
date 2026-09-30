"""FastAPI endpoints for Computer Vision analysis on citizen ground-truth media."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import CitizenReport
from backend.app.schemas.ai_cv import CVAnalysisResult, CVAnalysisTriggerRequest
from backend.app.services.ai_cv.pipeline import CVOrchestrator

router = APIRouter(prefix="/cv", tags=["Computer Vision & Media Intelligence"])


@router.post("/analyze")
async def analyze_direct(
    file: UploadFile = File(...),
    reported_flood: bool = Form(True),
):
    """Directly analyze an uploaded photo or video with CV pipeline without saving to DB."""
    content = await file.read()
    media_type = "video" if file.content_type and "video" in file.content_type else "photo"
    res = CVOrchestrator.analyze(content, media_type=media_type, reported_flood=reported_flood)
    return res._data



@router.post("/analyze/{report_id}", response_model=CVAnalysisResult)
def trigger_cv_analysis(
    report_id: str,
    payload: CVAnalysisTriggerRequest = CVAnalysisTriggerRequest(),
    db: Session = Depends(get_db),
):
    """Trigger or retrieve Computer Vision analysis on a citizen hazard report."""
    report = db.query(CitizenReport).filter(CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Citizen report '{report_id}' not found.",
        )

    # Return cached inference if already processed and not forced
    if report.cv_processed_at and not payload.force_recompute:
        return CVAnalysisResult(
            report_id=report.id,
            media_type=report.media_type,
            water_fraction=report.cv_water_fraction or 0.0,
            estimated_depth_m=report.cv_estimated_depth_m,
            debris_velocity_ms=report.cv_debris_velocity_ms,
            is_false_alarm=report.cv_is_false_alarm or False,
            confidence=report.cv_confidence or 0.5,
            model_version=report.cv_model_version or "EWS-CV-Cached",
            features=report.cv_features or {},
            processed_at=report.cv_processed_at,
        )

    # Execute CV inference pipeline
    analysis = CVOrchestrator.analyze_file(report.file_path, report.media_type)

    # Update database record
    report.cv_water_fraction = analysis["water_fraction"]
    report.cv_estimated_depth_m = analysis["estimated_depth_m"]
    report.cv_debris_velocity_ms = analysis["debris_velocity_ms"]
    report.cv_is_false_alarm = analysis["is_false_alarm"]
    report.cv_confidence = analysis["confidence"]
    report.cv_model_version = analysis["model_version"]
    report.cv_features = analysis["features"]
    report.cv_processed_at = analysis["processed_at"]

    # Append to audit trail
    audit_entry = {
        "action": "CV_ANALYSIS_EXECUTED",
        "model": analysis["model_version"],
        "confidence": analysis["confidence"],
        "water_fraction": analysis["water_fraction"],
        "is_false_alarm": analysis["is_false_alarm"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not report.audit_log:
        report.audit_log = []
    report.audit_log = report.audit_log + [audit_entry]

    db.commit()
    db.refresh(report)

    return CVAnalysisResult(
        report_id=report.id,
        media_type=report.media_type,
        water_fraction=report.cv_water_fraction,
        estimated_depth_m=report.cv_estimated_depth_m,
        debris_velocity_ms=report.cv_debris_velocity_ms,
        is_false_alarm=report.cv_is_false_alarm,
        confidence=report.cv_confidence,
        model_version=report.cv_model_version,
        features=report.cv_features or {},
        processed_at=report.cv_processed_at,
    )


@router.get("/reports-analyzed", response_model=List[Dict[str, Any]])
def list_analyzed_reports(
    village_id: Optional[str] = Query(None),
    min_water_fraction: float = Query(0.0, ge=0.0, le=1.0),
    exclude_false_alarms: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve citizen reports enriched with Computer Vision predictions."""
    query = db.query(CitizenReport).filter(CitizenReport.cv_processed_at.isnot(None))

    if village_id:
        query = query.filter(CitizenReport.village_id == village_id)

    if min_water_fraction > 0.0:
        query = query.filter(CitizenReport.cv_water_fraction >= min_water_fraction)

    if exclude_false_alarms:
        query = query.filter(CitizenReport.cv_is_false_alarm.is_(False))

    records = query.order_by(CitizenReport.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "village_id": r.village_id,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "media_type": r.media_type,
            "caption": r.caption,
            "reported_flood": r.reported_flood,
            "status": r.status,
            "water_fraction": r.cv_water_fraction,
            "estimated_depth_m": r.cv_estimated_depth_m,
            "debris_velocity_ms": r.cv_debris_velocity_ms,
            "is_false_alarm": r.cv_is_false_alarm,
            "confidence": r.cv_confidence,
            "model_version": r.cv_model_version,
            "processed_at": r.cv_processed_at.isoformat() if r.cv_processed_at else None,
            "features": r.cv_features or {},
        }
        for r in records
    ]


@router.get("/summary")
def get_cv_pipeline_summary(db: Session = Depends(get_db)):
    """Aggregate statistics on CV media inference performance."""
    total_processed = db.query(CitizenReport).filter(CitizenReport.cv_processed_at.isnot(None)).count()
    flagged_false_alarms = (
        db.query(CitizenReport)
        .filter(CitizenReport.cv_is_false_alarm.is_(True))
        .count()
    )
    high_water_reports = (
        db.query(CitizenReport)
        .filter(CitizenReport.cv_water_fraction >= 0.25)
        .count()
    )

    return {
        "status": "OPERATIONAL",
        "pipeline_version": "EWS-CV-Himalayan-v2.4",
        "total_media_processed": total_processed,
        "flagged_false_alarms": flagged_false_alarms,
        "high_water_inundations": high_water_reports,
        "supported_models": [
            "FloodwaterSegmentation_SegFormer",
            "StaffGauge_YOLOv8_Pose",
            "OpticalFlow_RAFT_Debris",
            "ZeroShot_CLIP_FalseAlarm",
        ],
    }


@router.post("/catchment-gnn/simulate")
def simulate_catchment_gnn(payload: Dict[str, Any]):
    """Simulate Catchment GNN hydrodynamic discharge and PINN residual Fs correction."""
    from backend.app.services.ai_cv.gnn_runoff import PINNResidualCorrector

    sample_villages = [
        {"id": f"VIL_UTK_{i:02d}", "name": f"Sub-basin {i}", "base_factor_of_safety": 1.20 if i < 6 else 1.45, "rainfall_rate_mm_h": 45.0, "slope_deg": 34.0, "soil_moisture": 0.72}
        for i in range(1, 15)
    ]
    rain_overrides = payload.get("hourly_rainfall_mm", {})
    for v in sample_villages:
        if v["id"] in rain_overrides:
            v["rainfall_rate_mm_h"] = float(rain_overrides[v["id"]])

    results = PINNResidualCorrector.apply_catchment_pinn(sample_villages)

    return {
        "nodes": {r["id"]: r for r in results},
        "edges": [{"from_node": "VIL_UTK_01", "to_node": "VIL_UTK_02", "flow_m3s": 38.5}],
        "summary": {
            "total_nodes_simulated": len(results),
            "critical_nodes": [r["id"] for r in results if r.get("is_unstable")],
        },
    }


