"""API endpoints for multi-channel emergency alerting, CAP 1.2, acks, community reports, and drills."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import Alert, Village, Recipient, AlertDelivery, CommunityReport, Officer
from backend.app.core.security import require_officer_role
from backend.app.services.alerting.cap import generate_cap_12_xml
from backend.app.services.alerting.fatigue import check_alert_suppression
from backend.app.services.alerting.orchestrator import AlertLadderOrchestrator
from backend.app.services.alerting.metrics import calculate_alert_reach, calculate_drill_report

router = APIRouter(tags=["alerting"])


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------

class AlertTriggerRequest(BaseModel):
    """Payload to trigger an emergency alert or exercise drill."""

    village_id: str = Field(..., description="Village ID to alert")
    tier: str = Field(..., description="Alert tier: WATCH, WARNING, EVACUATE")
    message: Optional[str] = Field(None, max_length=160, description="Directive message (max 160 chars)")
    is_drill: bool = Field(False, description="Flag for emergency exercise/drill")
    cooldown_minutes: int = Field(60, ge=1, description="Fatigue suppression cooldown in minutes")
    override_cooldown: bool = Field(False, description="Force override fatigue suppression")
    escalation_window_sec: float = Field(0.05, ge=0.0, description="Ladder wait window between channels (seconds)")


class AckRequest(BaseModel):
    """Acknowledgment payload from recipient or simulated webhook."""

    delivery_id: Optional[str] = Field(None, description="Specific delivery ID to acknowledge")
    alert_id: Optional[str] = Field(None, description="Alert ID for recipient acknowledgment")
    recipient_id: Optional[str] = Field(None, description="Recipient ID acknowledging the alert")


class CommunityReportCreate(BaseModel):
    """Citizen hazard report payload."""

    village_id: Optional[str] = Field(None, description="Village ID if known")
    lat: float = Field(..., description="Latitude coordinate")
    lon: float = Field(..., description="Longitude coordinate")
    photo_url: Optional[str] = Field(None, description="URL or data URI to field damage photograph")
    text: str = Field(..., min_length=3, description="Eye-witness hazard description")
    reporter_name: Optional[str] = Field(None, description="Reporter name")
    reporter_phone: Optional[str] = Field(None, description="Contact phone number")


class CommunityReportReview(BaseModel):
    """Official vetting and ground-truth validation payload."""

    status: str = Field(..., pattern="^(VERIFIED|REJECTED|PENDING_REVIEW)$", description="Review status")
    reviewed_by: str = Field(..., description="Officer name or ID vetting the report")
    review_notes: Optional[str] = Field(None, description="Notes on ground-truth verification")
    is_ground_truth_candidate: Optional[bool] = Field(True, description="Mark as ground-truth candidate for ML retrain")


# ---------------------------------------------------------
# Alert Trigger & CAP Endpoints
# ---------------------------------------------------------

@router.post("/alerts/trigger")
async def trigger_alert(
    request: AlertTriggerRequest,
    current_officer: Officer = Depends(require_officer_role(["officer", "admin"])),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger an emergency alert with fatigue control, CAP 1.2 XML, and ladder escalation."""
    village = db.query(Village).filter(Village.id == request.village_id).first()
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Village '{request.village_id}' not found.",
        )

    # 1. Alert Fatigue Suppression Check
    if not request.override_cooldown and not request.is_drill:
        is_suppressed, reason = check_alert_suppression(
            village_id=request.village_id,
            new_tier=request.tier,
            db=db,
            cooldown_minutes=request.cooldown_minutes,
        )
        if is_suppressed:
            return {
                "status": "SUPPRESSED",
                "message": reason,
                "village_id": request.village_id,
                "tier": request.tier,
                "cooldown_active": True,
            }

    # 2. Build Directive Message (Strictly <= 160 chars)
    msg = request.message
    if not msg:
        prefix = "[DRILL] " if request.is_drill else ""
        if request.tier.upper() in ["EVACUATE", "RED"]:
            msg = f"{prefix}EVACUATE NOW: High landslide threat at {village.name}. Move to high ground refuge shelter immediately."
        elif request.tier.upper() in ["WARNING", "ORANGE"]:
            msg = f"{prefix}WARNING: Heavy rain triggering slope instability at {village.name}. Prepare grab-bags and monitor sirens."
        else:
            msg = f"{prefix}WATCH: Weather radar shows intense rainfall upstream of {village.name}. Stay alert."
    msg = msg[:160]

    # 3. Create Alert Record
    alert_id = f"ALT_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    cooldown_until = now + timedelta(minutes=request.cooldown_minutes)

    alert_obj = Alert(
        id=alert_id,
        village_id=village.id,
        tier=request.tier.upper(),
        message=msg,
        drill_flag=request.is_drill,
        created_at=now,
        cooldown_until=cooldown_until,
    )

    # 4. Generate CAP 1.2 XML
    cap_xml = generate_cap_12_xml(alert=alert_obj, village=village, is_drill=request.is_drill)
    alert_obj.cap_xml = cap_xml

    db.add(alert_obj)
    db.commit()
    db.refresh(alert_obj)

    # 5. Execute Fallback Alert Ladder
    orchestrator = AlertLadderOrchestrator()
    ladder_result = await orchestrator.execute_alert_ladder(
        alert_id=alert_obj.id,
        db=db,
        escalation_window_sec=request.escalation_window_sec,
    )

    return {
        "status": "DISPATCHED",
        "alert_id": alert_obj.id,
        "village_id": village.id,
        "tier": alert_obj.tier,
        "message": alert_obj.message,
        "is_drill": alert_obj.drill_flag,
        "cooldown_until": alert_obj.cooldown_until.isoformat() if alert_obj.cooldown_until else None,
        "ladder_execution": ladder_result,
        "cap_xml_preview": cap_xml[:400] + "...",
    }


@router.get("/alerts/{alert_id}/cap")
def get_alert_cap_xml(
    alert_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve official OASIS CAP 1.2 XML document for an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    if not alert.cap_xml:
        village = db.query(Village).filter(Village.id == alert.village_id).first()
        alert.cap_xml = generate_cap_12_xml(alert, village, is_drill=bool(alert.drill_flag))
        db.commit()

    return Response(content=alert.cap_xml, media_type="application/xml")


# ---------------------------------------------------------
# Acknowledgment & Reach Metrics Endpoints
# ---------------------------------------------------------

@router.post("/alerts/ack")
def acknowledge_alert(
    request: AckRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Track recipient acknowledgment via SMS/IVR reply, link tap, or volunteer check-in."""
    orchestrator = AlertLadderOrchestrator()

    if request.delivery_id:
        delivery = orchestrator.acknowledge_delivery(request.delivery_id, db)
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery '{request.delivery_id}' not found.",
            )
        return {
            "status": "ACKNOWLEDGED",
            "delivery_id": delivery.id,
            "alert_id": delivery.alert_id,
            "recipient_id": delivery.recipient_id,
            "acked_at": delivery.acked_at.isoformat() if delivery.acked_at else None,
        }

    elif request.alert_id and request.recipient_id:
        delivs = orchestrator.acknowledge_by_recipient(
            request.alert_id, request.recipient_id, db
        )
        if not delivs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No deliveries found for alert '{request.alert_id}' and recipient '{request.recipient_id}'.",
            )
        return {
            "status": "ACKNOWLEDGED",
            "alert_id": request.alert_id,
            "recipient_id": request.recipient_id,
            "acknowledged_deliveries_count": len(delivs),
            "acked_at": delivs[0].acked_at.isoformat() if delivs[0].acked_at else None,
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either 'delivery_id' or both 'alert_id' and 'recipient_id'.",
        )


@router.get("/alerts/{alert_id}/reach")
def get_alert_reach(
    alert_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve live reach percentage, channel breakdown, and vulnerable population stats."""
    try:
        return calculate_alert_reach(alert_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ---------------------------------------------------------
# Drill / Exercise Endpoints
# ---------------------------------------------------------

@router.post("/drills/trigger")
async def trigger_drill(
    request: AlertTriggerRequest,
    current_officer: Officer = Depends(require_officer_role(["officer", "admin"])),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger an emergency exercise evacuation drill with CAP status='Test'."""
    request.is_drill = True
    return await trigger_alert(request=request, current_officer=current_officer, db=db)


@router.get("/drills/{drill_id}/report")
def get_drill_participation_report(
    drill_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Measure community response and compliance rate for an evacuation drill."""
    try:
        return calculate_drill_report(drill_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ---------------------------------------------------------
# Community Hazard Reports Endpoints
# ---------------------------------------------------------

@router.post("/reports", status_code=status.HTTP_201_CREATED)
def submit_community_report(
    report_in: CommunityReportCreate,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Submit a crowd-sourced hazard observation with photo/location/text."""
    report_id = f"REP_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    report = CommunityReport(
        id=report_id,
        village_id=report_in.village_id,
        lat=report_in.lat,
        lon=report_in.lon,
        photo_url=report_in.photo_url,
        text=report_in.text,
        reporter_name=report_in.reporter_name,
        reporter_phone=report_in.reporter_phone,
        status="PENDING_REVIEW",
        is_ground_truth_candidate=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "status": "SUBMITTED",
        "report_id": report.id,
        "village_id": report.village_id,
        "lat": report.lat,
        "lon": report.lon,
        "is_ground_truth_candidate": report.is_ground_truth_candidate,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/reports")
def list_community_reports(
    village_id: Optional[str] = Query(None, description="Filter by village ID"),
    report_status: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING_REVIEW, VERIFIED, REJECTED)"),
    ground_truth_only: bool = Query(False, description="Filter only ground truth candidates"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List submitted community hazard observations with optional filtering."""
    query = db.query(CommunityReport)
    if village_id:
        query = query.filter(CommunityReport.village_id == village_id)
    if report_status:
        query = query.filter(CommunityReport.status == report_status.upper())
    if ground_truth_only:
        query = query.filter(CommunityReport.is_ground_truth_candidate == True)

    reports = query.order_by(CommunityReport.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "village_id": r.village_id,
            "lat": r.lat,
            "lon": r.lon,
            "photo_url": r.photo_url,
            "text": r.text,
            "reporter_name": r.reporter_name,
            "reporter_phone": r.reporter_phone,
            "status": r.status,
            "is_ground_truth_candidate": r.is_ground_truth_candidate,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "review_notes": r.review_notes,
        }
        for r in reports
    ]


@router.put("/reports/{report_id}/review")
def review_community_report(
    report_id: str,
    review_in: CommunityReportReview,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Review and vet citizen report as ground-truth candidate for ML retrain."""
    report = db.query(CommunityReport).filter(CommunityReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Community report '{report_id}' not found.",
        )

    report.status = review_in.status.upper()
    report.reviewed_by = review_in.reviewed_by
    report.reviewed_at = datetime.now(timezone.utc)
    report.review_notes = review_in.review_notes
    if review_in.is_ground_truth_candidate is not None:
        report.is_ground_truth_candidate = review_in.is_ground_truth_candidate

    db.commit()
    db.refresh(report)

    return {
        "status": "UPDATED",
        "report_id": report.id,
        "review_status": report.status,
        "is_ground_truth_candidate": report.is_ground_truth_candidate,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        "review_notes": report.review_notes,
    }
