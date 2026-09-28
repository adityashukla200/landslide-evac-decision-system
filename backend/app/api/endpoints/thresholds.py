"""API endpoints for managing and configuring village operational risk thresholds."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import Village, VillageThreshold
from ml.decision.thresholds import derive_village_thresholds

router = APIRouter(prefix="/thresholds", tags=["thresholds"])


class ThresholdUpdateRequest(BaseModel):
    """Payload for updating operational thresholds and cost parameters for a village."""

    watch_threshold: Optional[float] = Field(None, ge=0.001, le=0.999, description="WATCH tier trigger probability")
    warning_threshold: Optional[float] = Field(None, ge=0.001, le=0.999, description="WARNING tier trigger probability")
    evacuate_threshold: Optional[float] = Field(None, ge=0.001, le=0.999, description="EVACUATE tier trigger probability")
    cost_miss: Optional[float] = Field(None, gt=0.0, description="Relative cost of missed landslide detection")
    cost_false_alarm: Optional[float] = Field(None, gt=0.0, description="Relative cost of false alarm evacuation")
    max_alerts_per_year: Optional[int] = Field(None, ge=1, le=365, description="Maximum permitted annual alert episodes")
    modified_by: str = Field("district_official", min_length=2, max_length=64, description="Identifier of the official updating the threshold")
    change_reason: Optional[str] = Field(None, max_length=512, description="Operational justification for threshold adjustment")


class ThresholdResponse(BaseModel):
    """Operational risk thresholds and audit metadata for a village."""

    model_config = ConfigDict(from_attributes=True)

    village_id: str
    cost_miss: float
    cost_false_alarm: float
    bayes_optimal_threshold: float
    watch_threshold: float
    warning_threshold: float
    evacuate_threshold: float
    max_alerts_per_year: int
    last_modified_by: str
    last_modified_at: datetime
    change_reason: Optional[str] = None
    audit_log: List[Dict[str, Any]] = []



@router.get("/{village_id}", response_model=ThresholdResponse)
def get_village_thresholds(
    village_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve active Bayes-optimal thresholds, cost weights, and audit history for a village."""
    village = db.query(Village).filter(Village.id == village_id).first()
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Village with ID '{village_id}' not found.",
        )

    record = db.query(VillageThreshold).filter(VillageThreshold.village_id == village_id).first()
    if not record:
        # Auto-initialize if not present
        slope = 36.0 if village.elevation > 2000 else 24.0
        dist_stream = 40.0 if village.elevation < 1500 else 85.0
        disruption = 0.14 if village.elevation > 2200 else 0.08
        th_data = derive_village_thresholds({
            "village_id": village.id,
            "population": village.population,
            "slope": slope,
            "distance_to_stream": dist_stream,
            "evacuation_disruption_index": disruption,
        })
        record = VillageThreshold(
            village_id=village.id,
            cost_miss=th_data["cost_miss"],
            cost_false_alarm=th_data["cost_false_alarm"],
            bayes_optimal_threshold=th_data["bayes_optimal_threshold"],
            watch_threshold=th_data["watch_threshold"],
            warning_threshold=th_data["warning_threshold"],
            evacuate_threshold=th_data["evacuate_threshold"],
            max_alerts_per_year=th_data["max_alerts_per_year"],
            last_modified_by="system",
            last_modified_at=datetime.now(timezone.utc),
            change_reason="Auto-initialized from village topography",
            audit_log=[],
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


@router.put("/{village_id}", response_model=ThresholdResponse)
def update_village_thresholds(
    village_id: str,
    payload: ThresholdUpdateRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Allow authorized district disaster officials to adjust operational thresholds with audit tracking."""
    village = db.query(Village).filter(Village.id == village_id).first()
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Village with ID '{village_id}' not found.",
        )

    record = db.query(VillageThreshold).filter(VillageThreshold.village_id == village_id).first()
    if not record:
        # Create initial record
        record = VillageThreshold(
            village_id=village_id,
            cost_miss=2500.0,
            cost_false_alarm=80.0,
            bayes_optimal_threshold=0.031,
            watch_threshold=0.015,
            warning_threshold=0.025,
            evacuate_threshold=0.150,
            max_alerts_per_year=15,
            last_modified_by="system",
            last_modified_at=datetime.now(timezone.utc),
            audit_log=[],
        )
        db.add(record)

    # Determine proposed values for tier ordering check
    proposed_watch = payload.watch_threshold if payload.watch_threshold is not None else record.watch_threshold
    proposed_warning = payload.warning_threshold if payload.warning_threshold is not None else record.warning_threshold
    proposed_evacuate = payload.evacuate_threshold if payload.evacuate_threshold is not None else record.evacuate_threshold

    # Validate monotonic ordering: watch < warning < evacuate
    if not (proposed_watch < proposed_warning < proposed_evacuate):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Threshold hierarchy violation: must strictly satisfy watch < warning < evacuate. "
                f"Proposed: watch={proposed_watch}, warning={proposed_warning}, evacuate={proposed_evacuate}."
            ),
        )

    # Capture previous values for audit trail
    previous_snapshot = {
        "watch_threshold": record.watch_threshold,
        "warning_threshold": record.warning_threshold,
        "evacuate_threshold": record.evacuate_threshold,
        "cost_miss": record.cost_miss,
        "cost_false_alarm": record.cost_false_alarm,
        "max_alerts_per_year": record.max_alerts_per_year,
    }

    # Apply updates
    if payload.watch_threshold is not None:
        record.watch_threshold = round(payload.watch_threshold, 6)
    if payload.warning_threshold is not None:
        record.warning_threshold = round(payload.warning_threshold, 6)
    if payload.evacuate_threshold is not None:
        record.evacuate_threshold = round(payload.evacuate_threshold, 6)
    if payload.cost_miss is not None:
        record.cost_miss = round(payload.cost_miss, 2)
    if payload.cost_false_alarm is not None:
        record.cost_false_alarm = round(payload.cost_false_alarm, 2)
    if payload.max_alerts_per_year is not None:
        record.max_alerts_per_year = payload.max_alerts_per_year

    # Recompute bayes optimal if costs updated
    if payload.cost_miss is not None or payload.cost_false_alarm is not None:
        record.bayes_optimal_threshold = round(
            record.cost_false_alarm / (record.cost_false_alarm + record.cost_miss), 6
        )

    now = datetime.now(timezone.utc)
    record.last_modified_by = payload.modified_by
    record.last_modified_at = now
    record.change_reason = payload.change_reason

    # Append to audit log
    audit_entry = {
        "timestamp": now.isoformat(),
        "modified_by": payload.modified_by,
        "reason": payload.change_reason or "Operational adjustment by district official",
        "previous_values": previous_snapshot,
        "new_values": {
            "watch_threshold": record.watch_threshold,
            "warning_threshold": record.warning_threshold,
            "evacuate_threshold": record.evacuate_threshold,
            "cost_miss": record.cost_miss,
            "cost_false_alarm": record.cost_false_alarm,
            "max_alerts_per_year": record.max_alerts_per_year,
        },
    }

    current_log = list(record.audit_log) if record.audit_log else []
    current_log.append(audit_entry)
    record.audit_log = current_log

    db.commit()
    db.refresh(record)
    return record
