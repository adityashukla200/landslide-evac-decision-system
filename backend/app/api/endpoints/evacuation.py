"""API endpoint for evacuation readiness assessment, routing, and alert generation."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.evacuation import assess_evacuation_readiness

router = APIRouter(tags=["evacuation"])


class EvacuationAssessRequest(BaseModel):
    """Optional parameters for running dynamic evacuation readiness simulation."""

    current_rainfall_rate_mm_h: Optional[float] = Field(25.0, ge=0.0, description="Current precipitation intensity (mm/h)")
    rainfall_trend_rate: Optional[float] = Field(5.0, description="Rate of rainfall increase dR/dt (mm/h per hour)")
    model_probability: Optional[float] = Field(0.035, ge=0.0, le=1.0, description="Calibrated landslide failure probability")
    is_night: Optional[bool] = Field(False, description="Flag for nighttime evacuation conditions (applies visibility impedance)")
    vulnerable_priority: Optional[bool] = Field(False, description="Compute walking duration based on vulnerable speed (elderly/mobility-impaired)")


@router.post("/assess/{village_id}")
def assess_village_evacuation(
    village_id: str,
    request: Optional[EvacuationAssessRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Calculate time-to-impact, time-to-evacuate, available margin, alert stage, and multilingual messages for a village."""
    payload = request or EvacuationAssessRequest()
    try:
        assessment = assess_evacuation_readiness(
            village_id=village_id,
            db=db,
            current_rainfall_rate_mm_h=payload.current_rainfall_rate_mm_h or 25.0,
            rainfall_trend_rate=payload.rainfall_trend_rate if payload.rainfall_trend_rate is not None else 5.0,
            model_probability=payload.model_probability if payload.model_probability is not None else 0.035,
            is_night=bool(payload.is_night),
            vulnerable_priority=bool(payload.vulnerable_priority),
        )
        return assessment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evacuation assessment failed: {e}",
        )
