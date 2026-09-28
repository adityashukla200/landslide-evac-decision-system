"""
MQTT-based sensor simulator for 25 Uttarkashi/Chamoli villages.

Publishes to topics:
  sensors/{village_id}/soil_moisture   (vol. water content 0.0–1.0)
  sensors/{village_id}/rainfall        (mm accumulated in last 5 min)
  sensors/{village_id}/tilt            (degrees from vertical, 0.0–5.0)
  sensors/{village_id}/stream_level    (metres above base-flow datum)

Noise model:
  - Gaussian additive noise calibrated per sensor type.
  - Random dropout (configurable per-sensor; default ~3% of readings).
  - "Stuck sensor" fault: sensor freezes on one value for N consecutive cycles.
  - "Spike fault": single-sample outlier 3–5× normal range.
  - "Cross-sensor inconsistency fault": heavy rain injected with no matching
    soil-moisture rise (simulates a waterproof-casing crack in the rain gauge
    but damaged soil probe).

The simulator runs either in:
  - STANDALONE mode: publishes to a real MQTT broker (paho-mqtt).
  - IN-PROCESS mode: returns readings directly as Python dicts (no broker needed),
    useful for tests and the EWS pipeline when no broker is configured.
"""

from __future__ import annotations

import math
import time
import random
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Village Registry ───────────────────────────────────────────────────────
# 25 synthetic villages across Uttarkashi & Chamoli districts (Uttarakhand).
# Coordinates are approximate but physically plausible.
# 8 villages deliberately have no sensor (sensor_equipped=False) to exercise
# the virtual-sensor interpolator.

@dataclass
class VillageMetadata:
    id: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    slope_deg: float
    sensor_equipped: bool = True
    population: int = 500


VILLAGE_REGISTRY: List[VillageMetadata] = [
    VillageMetadata("V01", "Bhatwari",     30.932, 78.468, 1330, 28.5, True,  4218),
    VillageMetadata("V02", "Harsil",       31.074, 78.775, 2620, 34.1, True,  812),
    VillageMetadata("V03", "Maneri",       30.881, 78.515, 1170, 22.3, True,  1840),
    VillageMetadata("V04", "Uttarkashi",   30.729, 78.438,  890, 18.7, True,  6200),
    VillageMetadata("V05", "Dharali",      31.019, 78.709, 1840, 31.2, True,  620),
    VillageMetadata("V06", "Sukhi",        30.921, 78.490, 1290, 25.8, True,  380),
    VillageMetadata("V07", "Gangotri",     30.994, 78.939, 3048, 38.4, True,  142),
    VillageMetadata("V08", "Nelong",       31.210, 78.800, 3530, 29.6, True,  88),
    VillageMetadata("V09", "Chinyalisaur", 30.523, 78.590,  790, 14.2, True,  3100),
    VillageMetadata("V10", "Mori",         30.876, 78.282,  920, 19.5, True,  2200),
    VillageMetadata("V11", "Barkot",       30.800, 78.219,  1440, 26.3, True,  3800),
    VillageMetadata("V12", "Naugaon",      30.718, 78.316,  1180, 23.7, True,  2600),
    VillageMetadata("V13", "Dunda",        30.780, 78.480,  1050, 20.1, True,  1900),
    VillageMetadata("V14", "Joshimath",    30.561, 79.565,  1890, 33.6, True,  7200),
    VillageMetadata("V15", "Chamoli",      30.399, 79.320,  900, 17.4, True,  5400),
    VillageMetadata("V16", "Gopeshwar",    30.475, 79.309,  1309, 24.5, True,  4100),
    VillageMetadata("V17", "Kedarnath",    30.733, 79.066,  3553, 41.2, True,  85),
    VillageMetadata("V18", "Badrinath",    30.744, 79.493,  3133, 36.7, True,  2000),
    # --- Villages without physical sensors (virtual only) ---
    VillageMetadata("V19", "Gamri",        30.950, 78.510, 1400, 29.1, False, 280),
    VillageMetadata("V20", "Tiloth",       30.900, 78.560, 1250, 24.8, False, 150),
    VillageMetadata("V21", "Sangla",       30.870, 78.600, 1100, 21.3, False, 340),
    VillageMetadata("V22", "Agora",        31.050, 78.720, 1950, 32.0, False, 95),
    VillageMetadata("V23", "Dhatmir",      30.840, 78.340, 1320, 27.4, False, 210),
    VillageMetadata("V24", "Puranapani",   30.760, 78.440,  980, 22.0, False, 410),
    VillageMetadata("V25", "Raikholi",     30.960, 78.640, 1550, 30.5, False, 175),
]

# Village lookup dict
VILLAGE_BY_ID: Dict[str, VillageMetadata] = {v.id: v for v in VILLAGE_REGISTRY}


# ── Sensor Reading dataclass ───────────────────────────────────────────────

@dataclass
class RawReading:
    """Single raw sensor observation before trust validation."""
    village_id: str
    sensor_type: str          # soil_moisture | rainfall | tilt | stream_level
    value: float
    unit: str
    timestamp: str            # ISO 8601 UTC
    seq: int                  # monotonic sequence counter
    fault: Optional[str] = None  # None | "stuck" | "spike" | "dropout" | "cross_incon"
    is_synthetic: bool = True
    data_source_label: str = "SYNTHETIC — MQTT simulator"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Fault injectors ────────────────────────────────────────────────────────

class FaultInjector:
    """Stateful per-sensor fault injector."""

    def __init__(self, rng: np.random.Generator, dropout_rate: float = 0.03,
                 spike_rate: float = 0.015, stuck_rate: float = 0.008,
                 stuck_min_cycles: int = 4, stuck_max_cycles: int = 12):
        self.rng = rng
        self.dropout_rate = dropout_rate
        self.spike_rate = spike_rate
        self.stuck_rate = stuck_rate
        self.stuck_min = stuck_min_cycles
        self.stuck_max = stuck_max_cycles

        # Stuck-sensor state
        self._stuck_active = False
        self._stuck_value: Optional[float] = None
        self._stuck_remaining = 0

    def apply(self, clean_value: float, sensor_type: str) -> tuple[Optional[float], Optional[str]]:
        """Return (noisy_value_or_None, fault_tag)."""
        # 1. Dropout
        if self.rng.random() < self.dropout_rate:
            return None, "dropout"

        # 2. Stuck sensor
        if self._stuck_active:
            self._stuck_remaining -= 1
            if self._stuck_remaining <= 0:
                self._stuck_active = False
            return self._stuck_value, "stuck"

        if self.rng.random() < self.stuck_rate:
            self._stuck_active = True
            self._stuck_value = round(float(clean_value), 4)
            self._stuck_remaining = int(self.rng.integers(self.stuck_min, self.stuck_max + 1))
            return self._stuck_value, "stuck"

        # 3. Spike
        if self.rng.random() < self.spike_rate:
            spike_factor = float(self.rng.uniform(3.0, 6.0))
            # Spike can be above or below physical range (raw, unvalidated)
            direction = 1 if self.rng.random() < 0.7 else -1
            spiked = clean_value + direction * spike_factor * abs(clean_value + 0.1)
            return round(spiked, 4), "spike"

        # 4. Clean + Gaussian noise
        noise_scale = {
            "soil_moisture":  0.01,
            "rainfall":       0.40,
            "tilt":           0.05,
            "stream_level":   0.03,
        }.get(sensor_type, 0.02)
        noisy = clean_value + float(self.rng.normal(0.0, noise_scale))
        return round(noisy, 4), None


# ── Physics model for realistic sensor values ──────────────────────────────

class VillageSensorPhysics:
    """Generates physically plausible sensor readings for one village."""

    def __init__(self, village: VillageMetadata, seed: int):
        self.village = village
        self.rng = np.random.default_rng(seed)

        # Slow-varying state variables
        self._soil_moisture = float(self.rng.uniform(0.25, 0.45))
        self._stream_level = float(self.rng.uniform(0.5, 1.5))
        self._tilt = 0.0
        self._cumulative_rain_5min = 0.0

        # Monsoon seasonality
        doy = datetime.now(timezone.utc).timetuple().tm_yday
        self._monsoon_factor = float(np.exp(-0.5 * ((doy - 205.0) / 32.0) ** 2))

    def step(self) -> Dict[str, float]:
        """Advance one simulation step (~5 min) and return clean readings."""
        mf = self._monsoon_factor
        rng = self.rng

        # Rainfall (~Gamma process during monsoon)
        p_rain = 0.05 + 0.50 * mf
        if rng.random() < p_rain:
            orographic = 1.0 + 0.30 * math.exp(-0.5 * ((self.village.elevation_m - 1700.0) / 600.0) ** 2)
            raw_rain_mm_h = float(rng.gamma(shape=1.5, scale=4.0 * orographic))
        else:
            raw_rain_mm_h = 0.0
        # 5-minute accumulation
        self._cumulative_rain_5min = raw_rain_mm_h * 5.0 / 60.0

        # Soil moisture (slow RC integration)
        infiltration = 0.03 * self._cumulative_rain_5min
        evap = 0.001 if mf < 0.3 else 0.0002
        self._soil_moisture = float(np.clip(
            self._soil_moisture + infiltration - evap + float(rng.normal(0, 0.003)),
            0.05, 0.98
        ))

        # Stream level (fast response to rainfall)
        self._stream_level = float(np.clip(
            self._stream_level * 0.92 + 0.05 * self._cumulative_rain_5min + float(rng.normal(0, 0.04)),
            0.1, 12.0
        ))

        # Tilt (very slow creep + occasional seismic micro-jolt)
        seismic_jolt = float(rng.exponential(0.01)) if rng.random() < 0.005 else 0.0
        creep = 0.00002 * self._soil_moisture * self.village.slope_deg
        self._tilt = float(np.clip(
            self._tilt + creep + seismic_jolt + float(rng.normal(0, 0.005)),
            0.0, 5.0
        ))

        return {
            "soil_moisture": round(self._soil_moisture, 4),
            "rainfall":      round(self._cumulative_rain_5min, 3),
            "tilt":          round(self._tilt, 4),
            "stream_level":  round(self._stream_level, 3),
        }

    def inject_cross_inconsistency(self, readings: Dict[str, float]) -> Dict[str, float]:
        """Simulate sensor damage: spike rainfall but suppress soil moisture response."""
        patched = dict(readings)
        patched["rainfall"] = round(readings["rainfall"] * 6.0 + 15.0, 3)   # huge rain reported
        patched["soil_moisture"] = round(max(0.05, readings["soil_moisture"] - 0.10), 4)  # moisture drops
        return patched


# ── Sensor Simulator ───────────────────────────────────────────────────────

SENSOR_UNITS = {
    "soil_moisture": "m3/m3",
    "rainfall":      "mm",
    "tilt":          "deg",
    "stream_level":  "m",
}


class SensorSimulator:
    """
    MQTT-based IoT sensor simulator for 25 Uttarkashi/Chamoli villages.

    Usage (in-process, no broker):
        sim = SensorSimulator()
        batch = sim.step_all()   # returns List[RawReading]

    Usage (MQTT publish mode):
        sim = SensorSimulator(mqtt_host="localhost", mqtt_port=1883)
        sim.start()   # background thread; calls publish_callback per reading
        sim.stop()
    """

    # Cross-sensor inconsistency is injected at ~1% of steps per village
    CROSS_INCON_RATE = 0.01

    def __init__(
        self,
        seed: int = 42,
        mqtt_host: Optional[str] = None,
        mqtt_port: int = 1883,
        publish_interval_s: float = 300.0,   # 5 minutes
        publish_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.seed = seed
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.publish_interval_s = publish_interval_s
        self.publish_callback = publish_callback  # (topic, json_payload)

        self._seq = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        master_rng = np.random.default_rng(seed)

        # Per-village physics + fault injectors (sensor-equipped villages only)
        self._physics: Dict[str, VillageSensorPhysics] = {}
        self._faults: Dict[str, Dict[str, FaultInjector]] = {}
        self._cross_incon_rng: Dict[str, np.random.Generator] = {}

        for idx, village in enumerate(VILLAGE_REGISTRY):
            if not village.sensor_equipped:
                continue
            vseed = int(master_rng.integers(0, 2**31))
            self._physics[village.id] = VillageSensorPhysics(village, vseed)
            self._faults[village.id] = {}
            for stype in ("soil_moisture", "rainfall", "tilt", "stream_level"):
                fi_seed = int(master_rng.integers(0, 2**31))
                self._faults[village.id][stype] = FaultInjector(
                    rng=np.random.default_rng(fi_seed),
                    # Tilt sensors are slightly more reliable; rainfall most noisy
                    dropout_rate={"soil_moisture": 0.03, "rainfall": 0.04, "tilt": 0.02, "stream_level": 0.03}[stype],
                    spike_rate={"soil_moisture": 0.012, "rainfall": 0.020, "tilt": 0.008, "stream_level": 0.012}[stype],
                )
            self._cross_incon_rng[village.id] = np.random.default_rng(int(master_rng.integers(0, 2**31)))

    # ── Core step ──

    def step_all(self) -> List[RawReading]:
        """Advance one simulation tick for all sensor-equipped villages.
        Returns a flat list of RawReading objects (4 × num_equipped_villages)."""
        self._seq += 1
        ts = datetime.now(timezone.utc).isoformat()
        readings: List[RawReading] = []

        for village_id, physics in self._physics.items():
            village = VILLAGE_BY_ID[village_id]
            clean = physics.step()

            # Inject cross-sensor inconsistency occasionally
            ci_rng = self._cross_incon_rng[village_id]
            if ci_rng.random() < self.CROSS_INCON_RATE:
                cross_incon_applied = True
                clean = physics.inject_cross_inconsistency(clean)
            else:
                cross_incon_applied = False

            for stype, clean_val in clean.items():
                injector = self._faults[village_id][stype]
                noisy_val, fault_tag = injector.apply(clean_val, stype)

                # Cross inconsistency overrides fault tag on rainfall/soil_moisture pair
                if cross_incon_applied and stype in ("rainfall", "soil_moisture"):
                    fault_tag = "cross_incon"

                if noisy_val is None:
                    # Dropout: skip this reading entirely (simulates no MQTT message)
                    continue

                readings.append(RawReading(
                    village_id=village_id,
                    sensor_type=stype,
                    value=noisy_val,
                    unit=SENSOR_UNITS[stype],
                    timestamp=ts,
                    seq=self._seq,
                    fault=fault_tag,
                    is_synthetic=True,
                    data_source_label="SYNTHETIC — MQTT simulator",
                ))

        return readings

    # ── MQTT publish ──

    def _publish_loop(self) -> None:
        """Background thread publishing readings to MQTT broker."""
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError:
            logger.error("[SensorSimulator] paho-mqtt not installed. Cannot publish.")
            return

        client = mqtt.Client(client_id="ews_sensor_sim")
        client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        client.loop_start()

        import json

        while not self._stop_event.is_set():
            batch = self.step_all()
            for reading in batch:
                topic = f"sensors/{reading.village_id}/{reading.sensor_type}"
                payload = json.dumps(reading.to_dict())
                client.publish(topic, payload, qos=1, retain=False)
                if self.publish_callback:
                    self.publish_callback(topic, payload)

            self._stop_event.wait(self.publish_interval_s)

        client.loop_stop()
        client.disconnect()

    def start(self) -> None:
        """Start background MQTT publishing thread."""
        if self.mqtt_host is None:
            raise RuntimeError("Set mqtt_host before calling start().")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._publish_loop, daemon=True, name="sensor-sim")
        self._thread.start()
        logger.info(f"[SensorSimulator] Started publishing to {self.mqtt_host}:{self.mqtt_port}")

    def stop(self) -> None:
        """Stop the background publish loop gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("[SensorSimulator] Stopped.")

    # ── Convenience ──

    @property
    def equipped_village_ids(self) -> List[str]:
        return list(self._physics.keys())

    @property
    def total_equipped(self) -> int:
        return len(self._physics)
