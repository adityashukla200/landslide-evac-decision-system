"""FastAPI endpoints for Disaster Scenario Replay & Demonstration."""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.services.replay import get_replay_engine

router = APIRouter(prefix="/replay", tags=["Replay Engine"])


class RunReplayRequest(BaseModel):
    scenario_id: str = Field(
        default="bhatwari_debris_flow_synthetic",
        description="ID of the disaster scenario to replay",
    )
    kill_internet: bool = Field(
        default=False,
        description="If True, disables cloud telecom channels and exercises local edge siren / volunteer radio fallback",
    )
    speed_multiplier: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Speed multiplier for playback (for frontend animation timing)",
    )


@router.get("/scenarios", summary="List available historical and synthetic disaster scenarios")
def list_replay_scenarios() -> List[Dict[str, Any]]:
    """Return all available historical and calibrated synthetic event scenarios."""
    engine = get_replay_engine()
    return engine.list_scenarios()


@router.post("/run", summary="Execute disaster timeline replay simulation")
def run_replay_simulation(payload: RunReplayRequest) -> Dict[str, Any]:
    """Fast-forward through disaster timeline and return frame-by-frame EWS vs Baseline metrics."""
    engine = get_replay_engine()
    try:
        return engine.run_replay(
            scenario_id=payload.scenario_id,
            kill_internet=payload.kill_internet,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Replay simulation error: {str(err)}")
