"""FastAPI endpoints for the sensor subsystem.

GET  /sensors/status            — per-sensor trust status + dropout fractions
GET  /sensors/readings/latest   — latest trusted readings for all equipped villages
GET  /sensors/virtual           — latest virtual estimates for unequipped villages
POST /sensors/simulate/step     — advance simulator one tick, run trust layer, return results
GET  /sensors/registry          — full village registry (equipped + unequipped)
POST /sensors/trust/reset       — reset trust-layer state for a single sensor
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from backend.app.services.sensors.simulator import SensorSimulator, VILLAGE_REGISTRY
from backend.app.services.sensors.trust import SensorTrustLayer
from backend.app.services.sensors.virtual import VirtualSensorInterpolator

router = APIRouter(prefix="/sensors", tags=["Sensors"])

# ── Module-level singletons ────────────────────────────────────────────────
_sim    = SensorSimulator(seed=42)
_trust  = SensorTrustLayer()
_interp = VirtualSensorInterpolator(VILLAGE_REGISTRY, method="IDW")

# In-memory cache of the most recent trusted readings (updated on each step)
_latest_trusted: Dict[tuple, float] = {}
_latest_raw_batch: List[Dict] = []


# ── Request/response schemas ───────────────────────────────────────────────

class TrustResetRequest(BaseModel):
    village_id: str
    sensor_type: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/registry")
def get_registry() -> List[Dict[str, Any]]:
    """Return the full village registry with sensor equipment status."""
    return [
        {
            "id": v.id,
            "name": v.name,
            "lat": v.lat,
            "lon": v.lon,
            "elevation_m": v.elevation_m,
            "slope_deg": v.slope_deg,
            "sensor_equipped": v.sensor_equipped,
            "population": v.population,
        }
        for v in VILLAGE_REGISTRY
    ]


@router.post("/simulate/step")
def simulate_step() -> Dict[str, Any]:
    """
    Advance the sensor simulator one 5-minute tick.
    Applies the trust layer; caches trusted readings.
    Returns raw counts, trust outcomes, and first 40 readings as sample.
    """
    global _latest_trusted, _latest_raw_batch

    raw_batch = _sim.step_all()
    _latest_raw_batch = [r.to_dict() for r in raw_batch]

    trusted_map: Dict[tuple, float] = {}
    results = {"OK": 0, "SUSPECT": 0, "DEGRADED": 0, "REJECTED": 0, "dropout_skipped": 0}
    sample: List[Dict] = []

    for raw in raw_batch:
        tr = _trust.evaluate(raw)
        results[tr.reading.status] = results.get(tr.reading.status, 0) + 1
        if tr.passed:
            trusted_map[(raw.village_id, raw.sensor_type)] = tr.reading.value
        if len(sample) < 40:
            sample.append({
                "village_id": raw.village_id,
                "sensor_type": raw.sensor_type,
                "raw_value": raw.value,
                "status": tr.reading.status,
                "quality_flag": tr.reading.quality_flag,
                "z_score": tr.z_score,
            })

    _latest_trusted = trusted_map
    results["dropout_skipped"] = (
        _sim.total_equipped * 4 - len(raw_batch)  # 4 sensor types per village
    )

    virtual = _interp.interpolate_all(trusted_map)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seq": _sim._seq,
        "raw_count": len(raw_batch),
        "trust_summary": results,
        "virtual_count": len(virtual),
        "sample_readings": sample,
    }


@router.get("/readings/latest")
def get_latest_readings(
    village_id: Optional[str] = Query(None, description="Filter by village ID"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
) -> List[Dict[str, Any]]:
    """Return the most recent trusted reading for each (village, sensor_type) pair."""
    readings = []
    for (vid, stype), value in _latest_trusted.items():
        if village_id and vid != village_id:
            continue
        if sensor_type and stype != sensor_type:
            continue
        readings.append({"village_id": vid, "sensor_type": stype, "value": value})
    return readings


@router.get("/virtual")
def get_virtual_readings(
    village_id: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """Return virtual sensor estimates for unequipped villages."""
    virtual = _interp.interpolate_all(_latest_trusted)
    results = []
    for vr in virtual:
        if village_id and vr.village_id != village_id:
            continue
        results.append({
            "village_id": vr.village_id,
            "sensor_type": vr.sensor_type,
            "estimated_value": vr.estimated_value,
            "unit": vr.unit,
            "method": vr.method,
            "source_village_ids": vr.source_village_ids,
            "source_weights": vr.source_weights,
            "uncertainty_1sigma": vr.uncertainty_1sigma,
            "is_synthetic": vr.is_synthetic,
            "data_source_label": vr.data_source_label,
        })
    return results


@router.get("/status")
def get_sensor_status() -> Dict[str, Any]:
    """Return trust-layer status for all tracked sensors."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_villages": len(VILLAGE_REGISTRY),
        "equipped_villages": _sim.total_equipped,
        "unequipped_villages": len(VILLAGE_REGISTRY) - _sim.total_equipped,
        "sensor_trust": _trust.get_sensor_status(),
    }


@router.get("/cross-validate")
def cross_validate(
    sensor_type: str = Query("soil_moisture"),
    method: str = Query("IDW"),
) -> Dict[str, Any]:
    """Leave-one-out cross-validation of virtual sensor interpolation accuracy."""
    interp = VirtualSensorInterpolator(VILLAGE_REGISTRY, method=method)
    cv = interp.cross_validate(_latest_trusted, sensor_type=sensor_type)
    return {
        "sensor_type": sensor_type,
        "method": method,
        "n_equipped_used": cv["n"],
        "mae": cv["mae"],
        "rmse": cv["rmse"],
        "max_error": cv["max_error"],
        "note": "Leave-one-out cross-validation on equipped villages only.",
    }


@router.post("/trust/reset")
def reset_trust(req: TrustResetRequest) -> Dict[str, str]:
    """Reset trust-layer history for a specific sensor (after recalibration)."""
    valid_types = {"soil_moisture", "rainfall", "tilt", "stream_level"}
    if req.sensor_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"sensor_type must be one of {sorted(valid_types)}",
        )
    _trust.reset_sensor(req.village_id, req.sensor_type)
    return {
        "status": "reset",
        "village_id": req.village_id,
        "sensor_type": req.sensor_type,
    }
