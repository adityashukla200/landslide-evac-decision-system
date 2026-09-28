"""
Virtual Sensor Interpolator — estimates soil moisture (and other fields) for
villages that have no physical IoT sensor.

Method selection:
  - IDW  (Inverse-Distance Weighting): fast, no external deps, default.
  - Kriging: Ordinary Kriging via `pykrige` if installed; falls back to IDW.

Both methods apply an orographic correction factor:
  elevation_factor = 1 + 0.15 * (elevation_delta_m / 500)
  (higher elevation → slightly higher soil moisture retention due to reduced
  evapotranspiration; empirical from Uttarakhand hill-soil studies).

Cross-validation utility is included to assess interpolation quality using
leave-one-out on equipped villages.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Data container ─────────────────────────────────────────────────────────

@dataclass
class VirtualReading:
    """Estimated sensor reading for an unequipped village."""
    village_id: str
    sensor_type: str
    estimated_value: float
    unit: str
    method: str                     # "IDW" | "Kriging"
    source_village_ids: List[str]   # which neighbours contributed
    source_weights: List[float]     # normalised weights (sum = 1.0)
    uncertainty_1sigma: float       # std of weighted residuals
    is_synthetic: bool = True
    data_source_label: str = "VIRTUAL — interpolated from neighbours"


# ── Elevation correction ───────────────────────────────────────────────────

def _elevation_factor(target_elev: float, source_elev: float) -> float:
    """Correction for elevation difference between source and target village."""
    delta = target_elev - source_elev
    # Positive delta → higher target → slightly wetter (less evap)
    factor = 1.0 + 0.15 * (delta / 500.0)
    return float(np.clip(factor, 0.70, 1.30))


# ── IDW core ──────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(max(0.0, a)))


def _idw_estimate(
    target_lat: float,
    target_lon: float,
    target_elev: float,
    source_lats: np.ndarray,
    source_lons: np.ndarray,
    source_elevs: np.ndarray,
    source_values: np.ndarray,
    source_ids: List[str],
    power: float = 2.0,
    max_neighbours: int = 6,
    min_dist_km: float = 0.05,
) -> Tuple[float, List[str], List[float], float]:
    """
    IDW interpolation with elevation correction and uncertainty estimate.
    Returns (estimated_value, source_ids_used, weights, uncertainty_1sigma).
    """
    distances = np.array([
        _haversine_km(target_lat, target_lon, source_lats[i], source_lons[i])
        for i in range(len(source_lats))
    ])

    # Check for coincident point (exact hit — shouldn't happen, but guard)
    min_d = distances.min()
    if min_d < min_dist_km:
        idx = int(distances.argmin())
        return float(source_values[idx]), [source_ids[idx]], [1.0], 0.0

    # Restrict to nearest max_neighbours
    order = np.argsort(distances)[:max_neighbours]
    dists = distances[order]
    vals  = source_values[order]
    elevs = source_elevs[order]
    ids   = [source_ids[i] for i in order]

    # Elevation-corrected values
    corrected = np.array([
        vals[i] * _elevation_factor(target_elev, elevs[i])
        for i in range(len(vals))
    ])

    # IDW weights
    weights = 1.0 / (dists ** power)
    weights /= weights.sum()

    estimate = float(np.dot(weights, corrected))

    # Uncertainty: weighted std of source values
    variance = float(np.dot(weights, (corrected - estimate) ** 2))
    uncertainty = math.sqrt(variance)

    return estimate, ids, weights.tolist(), uncertainty


# ── Kriging core (optional) ────────────────────────────────────────────────

def _kriging_estimate(
    target_lat: float,
    target_lon: float,
    target_elev: float,
    source_lats: np.ndarray,
    source_lons: np.ndarray,
    source_elevs: np.ndarray,
    source_values: np.ndarray,
    source_ids: List[str],
) -> Tuple[float, List[str], List[float], float]:
    """Ordinary Kriging via pykrige. Falls back to IDW if not available."""
    try:
        from pykrige.ok import OrdinaryKriging  # type: ignore

        # Apply elevation correction to source values
        corrected = np.array([
            source_values[i] * _elevation_factor(target_elev, source_elevs[i])
            for i in range(len(source_values))
        ])

        ok = OrdinaryKriging(
            source_lons, source_lats, corrected,
            variogram_model="spherical",
            verbose=False,
            enable_plotting=False,
        )
        z, variance = ok.execute("points", np.array([target_lon]), np.array([target_lat]))
        estimate = float(z[0])
        uncertainty = math.sqrt(max(0.0, float(variance[0])))

        # Compute approximate weights from kriging system (not trivial; approximate via IDW)
        _, ids_used, weights, _ = _idw_estimate(
            target_lat, target_lon, target_elev,
            source_lats, source_lons, source_elevs, source_values, source_ids,
        )
        return estimate, ids_used, weights, uncertainty

    except ImportError:
        logger.debug("[VirtualSensor] pykrige not installed; falling back to IDW.")
        return _idw_estimate(
            target_lat, target_lon, target_elev,
            source_lats, source_lons, source_elevs, source_values, source_ids,
        )


# ── Main interpolator class ────────────────────────────────────────────────

class VirtualSensorInterpolator:
    """
    Estimates sensor readings for unequipped villages using spatial interpolation.

    Usage:
        interp = VirtualSensorInterpolator(village_registry, method="IDW")
        # After each simulator step:
        trusted_readings = {(v_id, s_type): value, ...}
        virtual = interp.interpolate_all(trusted_readings)
    """

    SUPPORTED_TYPES = ("soil_moisture", "rainfall", "tilt", "stream_level")
    UNITS = {"soil_moisture": "m3/m3", "rainfall": "mm", "tilt": "deg", "stream_level": "m"}
    # Physical clipping ranges for interpolated outputs
    CLIP = {
        "soil_moisture":  (0.0,   1.0),
        "rainfall":       (0.0, 200.0),
        "tilt":           (0.0,  10.0),
        "stream_level":   (0.0,  15.0),
    }

    def __init__(self, village_registry, method: str = "IDW"):
        """
        village_registry: list of VillageMetadata from simulator module.
        method: "IDW" (default) or "Kriging".
        """
        self.method = method.upper()
        self._all_villages = village_registry
        self._equipped    = [v for v in village_registry if v.sensor_equipped]
        self._unequipped  = [v for v in village_registry if not v.sensor_equipped]

        # Pre-cache equipped village arrays for fast lookup
        self._eq_lats  = np.array([v.lat          for v in self._equipped])
        self._eq_lons  = np.array([v.lon          for v in self._equipped])
        self._eq_elevs = np.array([v.elevation_m  for v in self._equipped])
        self._eq_ids   = [v.id                    for v in self._equipped]

    # ── Public ──────────────────────────────────────────────────────────

    def interpolate_all(
        self,
        trusted_readings: Dict[Tuple[str, str], float],
        timestamp: Optional[str] = None,
    ) -> List[VirtualReading]:
        """
        Estimate all sensor types for all unequipped villages.

        trusted_readings: {(village_id, sensor_type): value} — already quality-passed.
        Returns list of VirtualReading (one per unequipped village × sensor_type).
        """
        if timestamp is None:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat()

        results: List[VirtualReading] = []
        for stype in self.SUPPORTED_TYPES:
            # Gather source values from equipped villages that have this reading
            src_vals: List[float] = []
            src_indices: List[int] = []
            for i, vid in enumerate(self._eq_ids):
                key = (vid, stype)
                if key in trusted_readings:
                    src_vals.append(trusted_readings[key])
                    src_indices.append(i)

            if len(src_vals) < 2:
                logger.debug(f"[VirtualSensor] Not enough source readings for {stype}; skipping.")
                continue

            src_lats  = self._eq_lats[src_indices]
            src_lons  = self._eq_lons[src_indices]
            src_elevs = self._eq_elevs[src_indices]
            src_values = np.array(src_vals)
            src_ids   = [self._eq_ids[i] for i in src_indices]

            for v in self._unequipped:
                est, ids_used, weights, unc = self._estimate_single(
                    v.lat, v.lon, v.elevation_m,
                    src_lats, src_lons, src_elevs, src_values, src_ids,
                )
                # Clip to physical range
                lo, hi = self.CLIP[stype]
                est_clipped = float(np.clip(est, lo, hi))

                results.append(VirtualReading(
                    village_id=v.id,
                    sensor_type=stype,
                    estimated_value=round(est_clipped, 4),
                    unit=self.UNITS[stype],
                    method=self.method,
                    source_village_ids=ids_used,
                    source_weights=[round(w, 4) for w in weights],
                    uncertainty_1sigma=round(unc, 5),
                    is_synthetic=True,
                    data_source_label="VIRTUAL — interpolated from neighbours",
                ))

        return results

    def cross_validate(
        self,
        trusted_readings: Dict[Tuple[str, str], float],
        sensor_type: str = "soil_moisture",
    ) -> Dict[str, float]:
        """
        Leave-one-out cross-validation on equipped villages.

        Returns: {"mae": ..., "rmse": ..., "max_error": ..., "n": ...}
        """
        src_vals, src_indices = [], []
        for i, vid in enumerate(self._eq_ids):
            k = (vid, sensor_type)
            if k in trusted_readings:
                src_vals.append(trusted_readings[k])
                src_indices.append(i)

        if len(src_vals) < 3:
            return {"mae": None, "rmse": None, "max_error": None, "n": 0}

        errors: List[float] = []
        for leave_out in range(len(src_indices)):
            idx_loo = [j for j in range(len(src_indices)) if j != leave_out]
            loo_lats  = self._eq_lats[[src_indices[j]  for j in idx_loo]]
            loo_lons  = self._eq_lons[[src_indices[j]  for j in idx_loo]]
            loo_elevs = self._eq_elevs[[src_indices[j] for j in idx_loo]]
            loo_vals  = np.array([src_vals[j]           for j in idx_loo])
            loo_ids   = [self._eq_ids[src_indices[j]]   for j in idx_loo]

            target_idx = src_indices[leave_out]
            t_lat  = self._eq_lats[target_idx]
            t_lon  = self._eq_lons[target_idx]
            t_elev = self._eq_elevs[target_idx]

            est, _, _, _ = self._estimate_single(
                t_lat, t_lon, t_elev,
                loo_lats, loo_lons, loo_elevs, loo_vals, loo_ids,
            )
            errors.append(abs(est - src_vals[leave_out]))

        errs = np.array(errors)
        return {
            "mae": round(float(errs.mean()), 5),
            "rmse": round(float(np.sqrt((errs ** 2).mean())), 5),
            "max_error": round(float(errs.max()), 5),
            "n": len(errors),
            "method": self.method,
        }

    # ── Private ─────────────────────────────────────────────────────────

    def _estimate_single(
        self,
        t_lat: float, t_lon: float, t_elev: float,
        src_lats: np.ndarray, src_lons: np.ndarray, src_elevs: np.ndarray,
        src_vals: np.ndarray, src_ids: List[str],
    ) -> Tuple[float, List[str], List[float], float]:
        if self.method == "KRIGING":
            return _kriging_estimate(t_lat, t_lon, t_elev, src_lats, src_lons, src_elevs, src_vals, src_ids)
        return _idw_estimate(t_lat, t_lon, t_elev, src_lats, src_lons, src_elevs, src_vals, src_ids)
