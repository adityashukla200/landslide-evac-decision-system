"""
Sensor Trust Layer — quality-gates raw IoT readings before they enter the model.

Detection rules (in order):
1. **Physical range check** — value outside calibrated sensor operating range.
2. **Rolling z-score spike** — |z| > 3.5 over a rolling 20-sample window.
3. **Stuck-value detection** — standard deviation of the last 8 samples < epsilon.
4. **Dropout / missing rate** — if a sensor misses > 40% of expected readings in
   the last 30 minutes, mark as DEGRADED.
5. **Cross-sensor consistency** — heavy rainfall (>= RAIN_HEAVY_MM) with no
   matching soil moisture rise within 2 readings is physically inconsistent.
   Both sensors are marked SUSPECT until confirmed.

Output:
  TrustResult.status ∈ {"OK", "SUSPECT", "DEGRADED", "REJECTED"}
  REJECTED readings are never forwarded to the model.
  SUSPECT readings are forwarded with a quality_flag but carry reduced weight.
"""

from __future__ import annotations

import math
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Deque, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Physical operating ranges per sensor type ──────────────────────────────
PHYSICAL_RANGE: Dict[str, Tuple[float, float]] = {
    "soil_moisture":  (0.00, 1.00),
    "rainfall":       (0.00, 200.0),   # mm accumulated in 5 min (max plausible cloudburst)
    "tilt":           (0.00, 10.0),    # degrees; > 10° is structural collapse
    "stream_level":   (0.00, 15.0),    # metres
}

# ── Thresholds ──────────────────────────────────────────────────────────────
ZSCORE_THRESHOLD           = 3.5        # rolling z-score spike threshold
STUCK_WINDOW               = 8          # samples to check for stuck
STUCK_EPSILON              = 1e-5       # std < this → stuck
ROLLING_WINDOW             = 20         # samples for rolling stats
DROPOUT_WINDOW_SAMPLES     = 6          # 30 min / 5 min = 6 expected samples
DROPOUT_MAX_MISS_FRACTION  = 0.40       # >40% missing → DEGRADED
RAIN_HEAVY_MM              = 3.0        # 5-min accumulation ≥ this → heavy rain
MOISTURE_RISE_THRESHOLD    = 0.005      # expected minimum moisture rise per heavy-rain cycle
CROSS_INCON_LOOK_BACK      = 2          # readings to look back for moisture rise


# ── Output dataclasses ──────────────────────────────────────────────────────

@dataclass
class SensorReading:
    """A single validated reading forwarded from the trust layer."""
    village_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: str
    seq: int
    status: str                  # OK | SUSPECT | DEGRADED | REJECTED
    quality_flag: Optional[str]  # None or descriptive tag
    raw_value: float             # original value before any correction
    is_synthetic: bool = True


@dataclass
class TrustResult:
    """Outcome of running the trust layer on a single raw reading."""
    reading: SensorReading
    passed: bool                 # True if status is OK or SUSPECT (forwarded)
    rule_triggered: Optional[str]
    z_score: Optional[float] = None


# ── Per-sensor rolling state ────────────────────────────────────────────────

@dataclass
class _SensorState:
    history: Deque[float]      = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    recv_times: Deque[str]     = field(default_factory=lambda: deque(maxlen=DROPOUT_WINDOW_SAMPLES + 2))
    miss_count: int            = 0
    expected_count: int        = 0
    last_seq_seen: int         = 0
    suspect_cross_incon: bool  = False
    cross_incon_counter: int   = 0


class SensorTrustLayer:
    """
    Stateful per-sensor quality gate.

    Usage:
        trust = SensorTrustLayer()
        for raw in sim.step_all():
            result = trust.evaluate(raw)
            if result.passed:
                feed_to_model(result.reading)
    """

    def __init__(self, expected_interval_seq: int = 1):
        """
        expected_interval_seq: how many simulator ticks between readings (normally 1).
        """
        self._expected_interval = expected_interval_seq
        # keyed by (village_id, sensor_type)
        self._state: Dict[Tuple[str, str], _SensorState] = {}

    # ── Public ──

    def evaluate(self, raw) -> TrustResult:  # raw: RawReading from simulator
        """Evaluate a raw reading and return a TrustResult."""
        key = (raw.village_id, raw.sensor_type)
        state = self._state.setdefault(key, _SensorState())

        # Track dropout (gap in seq numbers)
        expected_seq = state.last_seq_seen + self._expected_interval
        if state.last_seq_seen > 0 and raw.seq > expected_seq:
            gap = raw.seq - state.last_seq_seen - 1
            state.miss_count += gap
            state.expected_count += gap
        state.expected_count += 1
        state.last_seq_seen = raw.seq
        state.recv_times.append(raw.timestamp)

        value = raw.value

        # ── Rule 1: Physical range ──────────────────────────────────────
        lo, hi = PHYSICAL_RANGE.get(raw.sensor_type, (-math.inf, math.inf))
        if not (lo <= value <= hi):
            return self._make_result(
                raw, state, value, "REJECTED", "physical_range_violation",
                passed=False,
            )

        # ── Rule 2: Rolling z-score spike ──────────────────────────────
        z_score: Optional[float] = None
        if len(state.history) >= 4:
            arr = np.array(state.history)
            mu, sigma = float(arr.mean()), float(arr.std())
            if sigma > 1e-9:
                z_score = (value - mu) / sigma
                if abs(z_score) > ZSCORE_THRESHOLD:
                    state.history.append(value)
                    return self._make_result(
                        raw, state, value, "REJECTED", "zscore_spike",
                        passed=False, z_score=z_score,
                    )

        # ── Rule 3: Stuck sensor ────────────────────────────────────────
        if len(state.history) >= STUCK_WINDOW:
            recent = list(state.history)[-STUCK_WINDOW:]
            if float(np.std(recent)) < STUCK_EPSILON:
                state.history.append(value)
                return self._make_result(
                    raw, state, value, "SUSPECT", "stuck_value",
                    passed=True, z_score=z_score,
                )

        # ── Rule 4: Dropout / degraded sensor ──────────────────────────
        if state.expected_count >= DROPOUT_WINDOW_SAMPLES:
            miss_frac = state.miss_count / max(state.expected_count, 1)
            if miss_frac > DROPOUT_MAX_MISS_FRACTION:
                # Still forward but mark DEGRADED
                state.history.append(value)
                return self._make_result(
                    raw, state, value, "DEGRADED",
                    f"dropout_{miss_frac:.0%}_missing",
                    passed=True, z_score=z_score,
                )

        # ── Rule 5: Cross-sensor consistency ───────────────────────────
        status, flag = self._cross_sensor_check(raw.village_id, raw.sensor_type, value, state)
        if flag:
            state.history.append(value)
            return self._make_result(
                raw, state, value, status, flag,
                passed=(status != "REJECTED"), z_score=z_score,
            )

        # ── All checks passed ───────────────────────────────────────────
        state.history.append(value)
        return self._make_result(raw, state, value, "OK", None, passed=True, z_score=z_score)

    def get_sensor_status(self) -> Dict[str, Dict]:
        """Return current trust status summary for all tracked sensors."""
        summary = {}
        for (vid, stype), st in self._state.items():
            miss_frac = (
                st.miss_count / max(st.expected_count, 1)
                if st.expected_count > 0 else 0.0
            )
            arr = np.array(st.history) if st.history else np.array([0.0])
            std_last8 = float(np.std(list(st.history)[-STUCK_WINDOW:])) if len(st.history) >= STUCK_WINDOW else None
            summary[f"{vid}:{stype}"] = {
                "samples_received": st.expected_count,
                "dropout_fraction": round(miss_frac, 3),
                "std_last8": round(std_last8, 6) if std_last8 is not None else None,
                "rolling_mean": round(float(arr.mean()), 4),
                "rolling_std": round(float(arr.std()), 4),
                "cross_incon_count": st.cross_incon_counter,
                "suspect_cross_incon": st.suspect_cross_incon,
            }
        return summary

    def reset_sensor(self, village_id: str, sensor_type: str) -> None:
        """Reset state for a single sensor (after sensor replacement/recalibration)."""
        key = (village_id, sensor_type)
        if key in self._state:
            del self._state[key]
            logger.info(f"[SensorTrust] Reset state for {village_id}:{sensor_type}")

    # ── Cross-sensor state shared across sensor types per village ──────

    # We store the rainfall + soil_moisture history per village in a class-level dict
    _cross_state: Dict[str, "_CrossState"] = {}

    @dataclass
    class _CrossState:
        recent_rain_heavy: Deque[bool] = field(default_factory=lambda: deque(maxlen=CROSS_INCON_LOOK_BACK + 1))
        recent_moisture: Deque[float] = field(default_factory=lambda: deque(maxlen=CROSS_INCON_LOOK_BACK + 1))
        suspect_until: int = 0   # seq number until which this village is suspect
        trigger_seq: int = 0

    def _get_cross(self, village_id: str) -> "_CrossState":
        if village_id not in self._cross_state:
            self._cross_state[village_id] = self._CrossState()
        return self._cross_state[village_id]

    def _cross_sensor_check(
        self,
        village_id: str,
        sensor_type: str,
        value: float,
        state: _SensorState,
    ) -> Tuple[str, Optional[str]]:
        """Detect heavy rain + no moisture rise inconsistency."""
        cross = self._get_cross(village_id)

        if sensor_type == "rainfall":
            is_heavy = value >= RAIN_HEAVY_MM
            cross.recent_rain_heavy.append(is_heavy)

            if is_heavy and len(cross.recent_moisture) >= CROSS_INCON_LOOK_BACK:
                # Check if soil moisture rose at all in last CROSS_INCON_LOOK_BACK steps
                moisture_list = list(cross.recent_moisture)
                moisture_rise = moisture_list[-1] - moisture_list[0]
                if moisture_rise < MOISTURE_RISE_THRESHOLD:
                    state.cross_incon_counter = getattr(state, 'cross_incon_counter', 0) + 1
                    state.suspect_cross_incon = True
                    cross.suspect_until = state.last_seq_seen + CROSS_INCON_LOOK_BACK + 1
                    return "SUSPECT", "cross_incon_rain_no_moisture_rise"

        elif sensor_type == "soil_moisture":
            cross.recent_moisture.append(value)
            if state.last_seq_seen <= cross.suspect_until and cross.suspect_until > 0:
                return "SUSPECT", "cross_incon_moisture_pair"

        return "OK", None

    # ── Internal helper ─────────────────────────────────────────────────────

    @staticmethod
    def _make_result(
        raw,
        state: _SensorState,
        value: float,
        status: str,
        flag: Optional[str],
        passed: bool,
        z_score: Optional[float] = None,
    ) -> TrustResult:
        if flag:
            logger.debug(
                f"[SensorTrust] {raw.village_id}:{raw.sensor_type} "
                f"→ {status} ({flag})  value={value}"
            )
        return TrustResult(
            reading=SensorReading(
                village_id=raw.village_id,
                sensor_type=raw.sensor_type,
                value=value,
                unit=raw.unit,
                timestamp=raw.timestamp,
                seq=raw.seq,
                status=status,
                quality_flag=flag,
                raw_value=raw.value,
                is_synthetic=raw.is_synthetic,
            ),
            passed=passed,
            rule_triggered=flag,
            z_score=round(z_score, 3) if z_score is not None else None,
        )
