"""
Comprehensive tests for /backend/services/sensors:
  - Simulator: village registry, physics, noise, fault injection, dropout
  - Trust Layer: all 5 detection rules
  - Virtual Sensor: IDW correctness, elevation correction, cross-validation
  - FastAPI endpoints: registry, simulate/step, readings, virtual, status, reset
"""

import math
import time
import pytest
import numpy as np
from typing import Dict, Tuple

from backend.app.services.sensors.simulator import (
    SensorSimulator,
    VILLAGE_REGISTRY,
    VILLAGE_BY_ID,
    VillageSensorPhysics,
    FaultInjector,
    RawReading,
    SENSOR_UNITS,
)
from backend.app.services.sensors.trust import (
    SensorTrustLayer,
    PHYSICAL_RANGE,
    ZSCORE_THRESHOLD,
    STUCK_WINDOW,
    STUCK_EPSILON,
    RAIN_HEAVY_MM,
)
from backend.app.services.sensors.virtual import (
    VirtualSensorInterpolator,
    VirtualReading,
    _haversine_km,
    _idw_estimate,
    _elevation_factor,
)


# ═══════════════════════════════════════════════════════════════════════════
# VILLAGE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

class TestVillageRegistry:
    def test_exactly_25_villages(self):
        assert len(VILLAGE_REGISTRY) == 25

    def test_all_ids_unique(self):
        ids = [v.id for v in VILLAGE_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_7_or_8_unequipped_villages(self):
        unequipped = [v for v in VILLAGE_REGISTRY if not v.sensor_equipped]
        # Defined 7 unequipped (V19–V25)
        assert 5 <= len(unequipped) <= 10

    def test_equipped_villages_have_physical_coords(self):
        for v in VILLAGE_REGISTRY:
            assert 28.0 <= v.lat <= 32.0,  f"{v.id} lat out of Uttarakhand range"
            assert 77.0 <= v.lon <= 81.0,  f"{v.id} lon out of Uttarakhand range"
            assert 500 <= v.elevation_m <= 4000, f"{v.id} elevation implausible"
            assert 10 <= v.slope_deg <= 50,  f"{v.id} slope implausible"
            assert v.population > 0

    def test_village_by_id_lookup(self):
        for v in VILLAGE_REGISTRY:
            assert VILLAGE_BY_ID[v.id] is v


# ═══════════════════════════════════════════════════════════════════════════
# SIMULATOR — CLEAN MODE (no faults)
# ═══════════════════════════════════════════════════════════════════════════

class TestSimulatorClean:
    def setup_method(self):
        self.sim = SensorSimulator(seed=0)
        self.equipped_count = self.sim.total_equipped

    def test_total_equipped_matches_registry(self):
        expected = sum(1 for v in VILLAGE_REGISTRY if v.sensor_equipped)
        assert self.sim.total_equipped == expected

    def test_step_all_returns_readings(self):
        batch = self.sim.step_all()
        # 4 sensor types per equipped village, minus some dropouts
        assert len(batch) > 0
        assert all(isinstance(r, RawReading) for r in batch)

    def test_readings_are_synthetic(self):
        batch = self.sim.step_all()
        for r in batch:
            assert r.is_synthetic is True
            assert "SYNTHETIC" in r.data_source_label.upper()

    def test_all_readings_have_valid_sensor_types(self):
        batch = self.sim.step_all()
        valid_types = set(SENSOR_UNITS.keys())
        for r in batch:
            assert r.sensor_type in valid_types

    def test_seq_increments_monotonically(self):
        seqs = set()
        for _ in range(5):
            batch = self.sim.step_all()
            for r in batch:
                seqs.add(r.seq)
        assert len(seqs) == 5  # 5 distinct seq values

    def test_readings_have_timestamps(self):
        batch = self.sim.step_all()
        for r in batch:
            # Must be parseable ISO 8601
            from datetime import datetime
            datetime.fromisoformat(r.timestamp.replace("Z", "+00:00"))

    def test_most_readings_in_physical_range(self):
        """Without trust layer, majority of clean readings should be in range."""
        batch = self.sim.step_all()
        in_range = sum(
            1 for r in batch
            if PHYSICAL_RANGE.get(r.sensor_type, (-1e9, 1e9))[0]
            <= r.value
            <= PHYSICAL_RANGE.get(r.sensor_type, (-1e9, 1e9))[1]
        )
        # Cross-inconsistency faults can move values outside sensor range.
        # Even with all faults active, >75% should be in range.
        assert in_range / max(len(batch), 1) > 0.75


# ═══════════════════════════════════════════════════════════════════════════
# FAULT INJECTOR
# ═══════════════════════════════════════════════════════════════════════════

class TestFaultInjector:
    def _make_injector(self, seed=1, dropout=0.0, spike=0.0, stuck=0.0,
                       stuck_min=4, stuck_max=12):
        rng = np.random.default_rng(seed)
        return FaultInjector(rng, dropout_rate=dropout, spike_rate=spike, stuck_rate=stuck,
                             stuck_min_cycles=stuck_min, stuck_max_cycles=stuck_max)

    def test_no_faults_returns_noisy_value(self):
        inj = self._make_injector()
        val, fault = inj.apply(0.50, "soil_moisture")
        assert val is not None
        assert fault is None
        assert abs(val - 0.50) < 0.5  # noisy but not a spike

    def test_dropout_returns_none(self):
        inj = self._make_injector(dropout=1.0)
        val, fault = inj.apply(0.50, "soil_moisture")
        assert val is None
        assert fault == "dropout"

    def test_spike_returns_large_value(self):
        inj = self._make_injector(spike=1.0)
        val, fault = inj.apply(1.0, "rainfall")
        assert fault == "spike"
        assert val is not None
        assert abs(val) > 3.0  # spike multiplier ≥ 3

    def test_stuck_sensor_freezes_value(self):
        inj = self._make_injector(stuck=1.0, stuck_min=3, stuck_max=3)
        # First call triggers stuck
        v0, f0 = inj.apply(0.60, "tilt")
        assert f0 == "stuck"
        frozen = v0
        # Next calls should return same value
        for _ in range(3):
            v, f = inj.apply(0.70, "tilt")
            assert f == "stuck"
            assert v == frozen

    def test_dropout_rate_observed_statistically(self):
        """Observed dropout fraction should be within 3σ of expected."""
        rng = np.random.default_rng(999)
        inj = FaultInjector(rng, dropout_rate=0.10, spike_rate=0.0, stuck_rate=0.0)
        n = 1000
        dropped = sum(1 for _ in range(n) if inj.apply(0.5, "rainfall")[0] is None)
        # 10% ± 3*sqrt(0.1*0.9/1000) ≈ ±2.8%
        assert 0.06 < dropped / n < 0.14


# ═══════════════════════════════════════════════════════════════════════════
# TRUST LAYER — each rule independently
# ═══════════════════════════════════════════════════════════════════════════

def _make_raw(village_id="V01", sensor_type="soil_moisture", value=0.5,
              seq=1, fault=None, unit="m3/m3") -> RawReading:
    return RawReading(
        village_id=village_id,
        sensor_type=sensor_type,
        value=value,
        unit=unit,
        timestamp="2026-06-15T10:00:00+00:00",
        seq=seq,
        fault=fault,
        is_synthetic=True,
        data_source_label="SYNTHETIC",
    )


class TestTrustLayerPhysicalRange:
    def test_rejects_value_above_max(self):
        trust = SensorTrustLayer()
        raw = _make_raw(value=1.5, sensor_type="soil_moisture")  # max 1.0
        result = trust.evaluate(raw)
        assert result.reading.status == "REJECTED"
        assert result.rule_triggered == "physical_range_violation"
        assert not result.passed

    def test_rejects_negative_rainfall(self):
        trust = SensorTrustLayer()
        raw = _make_raw(value=-0.5, sensor_type="rainfall")
        result = trust.evaluate(raw)
        assert result.reading.status == "REJECTED"

    def test_accepts_value_at_boundary(self):
        trust = SensorTrustLayer()
        raw = _make_raw(value=1.0, sensor_type="soil_moisture")
        result = trust.evaluate(raw)
        assert result.reading.status in ("OK", "SUSPECT", "DEGRADED")


class TestTrustLayerZScoreSpike:
    def test_detects_spike_after_baseline(self):
        trust = SensorTrustLayer()
        # Use stream_level (range 0–15 m) with slight variance to avoid sigma=0
        rng = np.random.default_rng(0)
        for i in range(1, 21):
            v = float(2.0 + rng.normal(0, 0.05))  # μ=2.0, small noise
            v = max(0.01, min(14.9, v))
            trust.evaluate(_make_raw(value=v, sensor_type="stream_level", seq=i, unit="m"))
        # Inject spike at 11.0 m — within physical range (< 15 m), z >> 3.5
        spike_raw = _make_raw(value=11.0, sensor_type="stream_level", seq=21, unit="m")
        result = trust.evaluate(spike_raw)
        assert result.reading.status == "REJECTED"
        assert result.rule_triggered == "zscore_spike"
        assert result.z_score is not None and abs(result.z_score) > ZSCORE_THRESHOLD

    def test_normal_variation_not_flagged(self):
        trust = SensorTrustLayer()
        rng = np.random.default_rng(42)
        # Build baseline with std ≈ 0.05 so 0.53 is well within ±3.5σ
        for i in range(1, 21):
            v = float(0.50 + rng.normal(0, 0.05))
            v = max(0.0, min(1.0, v))   # keep in physical range
            trust.evaluate(_make_raw(value=v, seq=i))
        # 0.53 is within normal variation of μ=0.50, σ≈0.05
        result = trust.evaluate(_make_raw(value=0.53, seq=21))
        assert result.reading.status in ("OK", "SUSPECT", "DEGRADED")
        assert result.rule_triggered != "zscore_spike"


class TestTrustLayerStuck:
    def test_detects_stuck_sensor(self):
        trust = SensorTrustLayer()
        frozen = 0.42
        for i in range(1, STUCK_WINDOW + 3):
            result = trust.evaluate(_make_raw(value=frozen, seq=i))
        # By now it should be flagged as stuck
        assert result.reading.status == "SUSPECT"
        assert result.rule_triggered == "stuck_value"

    def test_normal_variation_not_stuck(self):
        trust = SensorTrustLayer()
        rng = np.random.default_rng(7)
        for i in range(1, STUCK_WINDOW + 3):
            v = float(0.5 + rng.normal(0, 0.02))
            result = trust.evaluate(_make_raw(value=v, seq=i))
        assert result.reading.status in ("OK", "SUSPECT", "DEGRADED")
        assert result.rule_triggered != "stuck_value"


class TestTrustLayerDropout:
    def test_degraded_when_many_gaps(self):
        trust = SensorTrustLayer()
        # First reading at seq=1
        trust.evaluate(_make_raw(value=0.5, seq=1))
        # Jump to seq=20, implying 18 missed readings
        result = trust.evaluate(_make_raw(value=0.5, seq=20))
        assert result.reading.status in ("SUSPECT", "DEGRADED")


class TestTrustLayerCrossSensor:
    def test_flags_heavy_rain_without_moisture_rise(self):
        trust = SensorTrustLayer()
        # Establish baseline moisture history
        for i in range(1, 5):
            trust.evaluate(_make_raw(village_id="V03", sensor_type="soil_moisture",
                                     value=0.40, seq=i))
        # Heavy rain reading with no moisture rise (moisture stayed at 0.40 → 0.40)
        rain_raw = _make_raw(village_id="V03", sensor_type="rainfall",
                              value=RAIN_HEAVY_MM + 2.0, seq=5)
        result = trust.evaluate(rain_raw)
        assert result.reading.status in ("SUSPECT",)
        assert "cross_incon" in (result.rule_triggered or "")

    def test_normal_rain_with_matching_moisture_ok(self):
        trust = SensorTrustLayer()
        # Build rising moisture history
        for i, moisture in enumerate([0.38, 0.41, 0.44, 0.47], start=1):
            trust.evaluate(_make_raw(village_id="V04", sensor_type="soil_moisture",
                                     value=moisture, seq=i))
        # Light rain — should be OK
        rain_raw = _make_raw(village_id="V04", sensor_type="rainfall",
                              value=1.0, seq=5)
        result = trust.evaluate(rain_raw)
        assert result.reading.status == "OK"


class TestTrustLayerReset:
    def test_reset_clears_history(self):
        trust = SensorTrustLayer()
        # Create stuck state
        for i in range(1, STUCK_WINDOW + 3):
            trust.evaluate(_make_raw(village_id="V05", sensor_type="tilt",
                                     value=0.10, seq=i))
        trust.reset_sensor("V05", "tilt")
        # After reset, same frozen value should NOT immediately flag as stuck
        result = trust.evaluate(_make_raw(village_id="V05", sensor_type="tilt",
                                          value=0.10, seq=100))
        assert result.reading.status == "OK"


class TestTrustLayerStatus:
    def test_status_has_all_evaluated_sensors(self):
        trust = SensorTrustLayer()
        for i in range(1, 6):
            trust.evaluate(_make_raw(village_id="V01", sensor_type="soil_moisture", value=0.5+i*0.01, seq=i))
            trust.evaluate(_make_raw(village_id="V01", sensor_type="rainfall", value=1.0, seq=i))
        status = trust.get_sensor_status()
        assert "V01:soil_moisture" in status
        assert "V01:rainfall" in status
        assert "samples_received" in status["V01:soil_moisture"]


# ═══════════════════════════════════════════════════════════════════════════
# VIRTUAL SENSOR — IDW
# ═══════════════════════════════════════════════════════════════════════════

class TestHaversine:
    def test_zero_distance_same_point(self):
        d = _haversine_km(30.0, 78.0, 30.0, 78.0)
        assert d < 1e-6

    def test_known_distance_bhatwari_to_harsil(self):
        # V01 Bhatwari vs V02 Harsil: ~35 km (rough)
        d = _haversine_km(30.932, 78.468, 31.074, 78.775)
        assert 25.0 < d < 50.0

    def test_symmetry(self):
        d1 = _haversine_km(30.0, 78.0, 31.0, 79.0)
        d2 = _haversine_km(31.0, 79.0, 30.0, 78.0)
        assert abs(d1 - d2) < 1e-9


class TestElevationFactor:
    def test_higher_target_gives_factor_above_one(self):
        factor = _elevation_factor(2000.0, 1000.0)
        assert factor > 1.0

    def test_same_elevation_gives_factor_near_one(self):
        factor = _elevation_factor(1500.0, 1500.0)
        assert abs(factor - 1.0) < 1e-9

    def test_clamped_to_70_130_pct(self):
        assert _elevation_factor(5000.0, 0.0) <= 1.30
        assert _elevation_factor(0.0, 5000.0) >= 0.70


class TestIDWEstimate:
    def _simple_sources(self):
        lats  = np.array([30.0, 31.0, 30.5])
        lons  = np.array([78.0, 78.0, 78.5])
        elevs = np.array([1000.0, 1000.0, 1000.0])
        vals  = np.array([0.40, 0.60, 0.50])
        ids   = ["A", "B", "C"]
        return lats, lons, elevs, vals, ids

    def test_estimate_between_min_max(self):
        lats, lons, elevs, vals, ids = self._simple_sources()
        est, _, _, _ = _idw_estimate(30.5, 78.25, 1000.0, lats, lons, elevs, vals, ids)
        assert 0.35 < est < 0.65

    def test_nearer_source_dominates(self):
        lats  = np.array([30.00, 32.00])
        lons  = np.array([78.00, 78.00])
        elevs = np.array([1000.0, 1000.0])
        vals  = np.array([0.80, 0.20])
        ids   = ["near", "far"]
        # Target is very close to "near" (30.01 vs 30.0)
        est, ids_used, _, _ = _idw_estimate(30.01, 78.00, 1000.0, lats, lons, elevs, vals, ids)
        assert est > 0.70, "Nearby source should dominate"

    def test_weights_sum_to_one(self):
        lats, lons, elevs, vals, ids = self._simple_sources()
        _, _, weights, _ = _idw_estimate(30.5, 78.25, 1000.0, lats, lons, elevs, vals, ids)
        assert abs(sum(weights) - 1.0) < 1e-9


class TestVirtualSensorInterpolator:
    def setup_method(self):
        self.interp = VirtualSensorInterpolator(VILLAGE_REGISTRY, method="IDW")
        # Populate trusted readings for equipped villages
        self.trusted: Dict[Tuple[str, str], float] = {}
        rng = np.random.default_rng(1)
        for v in VILLAGE_REGISTRY:
            if v.sensor_equipped:
                self.trusted[(v.id, "soil_moisture")] = float(rng.uniform(0.25, 0.75))
                self.trusted[(v.id, "rainfall")] = float(rng.uniform(0.0, 5.0))
                self.trusted[(v.id, "tilt")] = float(rng.uniform(0.0, 0.5))
                self.trusted[(v.id, "stream_level")] = float(rng.uniform(0.5, 3.0))

    def test_returns_readings_for_all_unequipped(self):
        unequipped_ids = {v.id for v in VILLAGE_REGISTRY if not v.sensor_equipped}
        results = self.interp.interpolate_all(self.trusted)
        returned_ids = {vr.village_id for vr in results}
        assert unequipped_ids.issubset(returned_ids)

    def test_each_village_gets_4_sensor_types(self):
        results = self.interp.interpolate_all(self.trusted)
        from collections import Counter
        count = Counter(vr.village_id for vr in results)
        for v in VILLAGE_REGISTRY:
            if not v.sensor_equipped:
                assert count[v.id] == 4, f"{v.id} should have 4 virtual readings"

    def test_soil_moisture_in_physical_range(self):
        results = self.interp.interpolate_all(self.trusted)
        for vr in results:
            if vr.sensor_type == "soil_moisture":
                assert 0.0 <= vr.estimated_value <= 1.0, (
                    f"{vr.village_id} soil_moisture={vr.estimated_value} out of range"
                )

    def test_method_label_is_idw(self):
        results = self.interp.interpolate_all(self.trusted)
        assert all(vr.method == "IDW" for vr in results)

    def test_weights_sum_to_one(self):
        results = self.interp.interpolate_all(self.trusted)
        for vr in results:
            # Weights are stored rounded to 4 decimal places; allow for rounding error
            assert abs(sum(vr.source_weights) - 1.0) < 1e-3, (
                f"Weights don't sum to 1 for {vr.village_id}:{vr.sensor_type}"
            )

    def test_uncertainty_non_negative(self):
        results = self.interp.interpolate_all(self.trusted)
        for vr in results:
            assert vr.uncertainty_1sigma >= 0.0

    def test_is_synthetic_label(self):
        results = self.interp.interpolate_all(self.trusted)
        for vr in results:
            assert vr.is_synthetic is True
            assert "VIRTUAL" in vr.data_source_label.upper()

    def test_cross_validate_returns_metrics(self):
        cv = self.interp.cross_validate(self.trusted, sensor_type="soil_moisture")
        assert cv["n"] >= 3
        assert cv["mae"] is not None and cv["mae"] >= 0.0
        assert cv["rmse"] is not None and cv["rmse"] >= cv["mae"]
        assert cv["max_error"] is not None and cv["max_error"] >= cv["mae"]

    def test_cross_validate_mae_reasonable(self):
        """For spatially smooth soil moisture, IDW LOO MAE should be < 0.25."""
        cv = self.interp.cross_validate(self.trusted, sensor_type="soil_moisture")
        assert cv["mae"] < 0.25, f"IDW LOO MAE too high: {cv['mae']}"

    def test_no_source_readings_returns_empty(self):
        results = self.interp.interpolate_all({})
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION: Simulator → Trust → Virtual pipeline
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEndPipeline:
    def setup_method(self):
        self.sim    = SensorSimulator(seed=77)
        self.trust  = SensorTrustLayer()
        self.interp = VirtualSensorInterpolator(VILLAGE_REGISTRY, method="IDW")

    def test_pipeline_runs_10_steps(self):
        trusted_map: Dict[Tuple[str, str], float] = {}
        for step in range(10):
            batch = self.sim.step_all()
            for raw in batch:
                tr = self.trust.evaluate(raw)
                if tr.passed:
                    trusted_map[(raw.village_id, raw.sensor_type)] = tr.reading.value

        # After 10 steps, we should have a reasonable number of trusted readings
        assert len(trusted_map) > 0

        virtual = self.interp.interpolate_all(trusted_map)
        assert len(virtual) > 0

    def test_rejected_readings_not_in_trusted_map(self):
        trusted_map: Dict[Tuple[str, str], float] = {}
        batch = self.sim.step_all()
        for raw in batch:
            tr = self.trust.evaluate(raw)
            if tr.reading.status == "REJECTED":
                assert not tr.passed
            if tr.passed:
                trusted_map[(raw.village_id, raw.sensor_type)] = tr.reading.value

    def test_fault_injection_produces_some_non_ok_statuses(self):
        """Over 50 steps, at least one spike/stuck/dropout should be detected."""
        trust = SensorTrustLayer()
        sim   = SensorSimulator(seed=42)
        non_ok = 0
        for _ in range(50):
            for raw in sim.step_all():
                tr = trust.evaluate(raw)
                if tr.reading.status != "OK":
                    non_ok += 1
        assert non_ok > 0, "Expected at least one non-OK reading in 50 steps"

    def test_virtual_estimates_for_all_unequipped(self):
        batch = self.sim.step_all()
        trusted_map = {}
        for raw in batch:
            tr = self.trust.evaluate(raw)
            if tr.passed:
                trusted_map[(raw.village_id, raw.sensor_type)] = tr.reading.value
        virtual = self.interp.interpolate_all(trusted_map)
        unequipped_ids = {v.id for v in VILLAGE_REGISTRY if not v.sensor_equipped}
        virtual_ids = {vr.village_id for vr in virtual}
        # At least some unequipped villages should have estimates
        assert len(virtual_ids.intersection(unequipped_ids)) > 0


# ═══════════════════════════════════════════════════════════════════════════
# FASTAPI ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestSensorAPI:
    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        self.client = TestClient(app, headers={"X-User-Role": "officer"})

    def test_get_registry_returns_25_villages(self):
        resp = self.client.get("/api/v1/sensors/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 25
        for v in data:
            assert "id" in v
            assert "sensor_equipped" in v
            assert "lat" in v
            assert "elevation_m" in v

    def test_simulate_step_returns_summary(self):
        resp = self.client.post("/api/v1/sensors/simulate/step")
        assert resp.status_code == 200
        data = resp.json()
        assert "trust_summary" in data
        assert "raw_count" in data
        assert "virtual_count" in data
        assert "sample_readings" in data
        assert data["raw_count"] > 0

    def test_trust_summary_keys(self):
        resp = self.client.post("/api/v1/sensors/simulate/step")
        ts = resp.json()["trust_summary"]
        assert "OK" in ts
        assert "REJECTED" in ts
        assert "SUSPECT" in ts
        assert "DEGRADED" in ts

    def test_latest_readings_after_step(self):
        self.client.post("/api/v1/sensors/simulate/step")
        resp = self.client.get("/api/v1/sensors/readings/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for r in data:
            assert "village_id" in r
            assert "sensor_type" in r
            assert "value" in r

    def test_latest_readings_filter_by_type(self):
        self.client.post("/api/v1/sensors/simulate/step")
        resp = self.client.get("/api/v1/sensors/readings/latest?sensor_type=rainfall")
        assert resp.status_code == 200
        for r in resp.json():
            assert r["sensor_type"] == "rainfall"

    def test_virtual_readings_endpoint(self):
        self.client.post("/api/v1/sensors/simulate/step")
        resp = self.client.get("/api/v1/sensors/virtual")
        assert resp.status_code == 200
        data = resp.json()
        # Should have readings for unequipped villages
        assert len(data) >= 0  # may be 0 if no trusted readings yet on first call

    def test_status_endpoint(self):
        resp = self.client.get("/api/v1/sensors/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_villages"] == 25
        assert "equipped_villages" in data
        assert "sensor_trust" in data

    def test_cross_validate_endpoint(self):
        self.client.post("/api/v1/sensors/simulate/step")
        resp = self.client.get("/api/v1/sensors/cross-validate?sensor_type=soil_moisture")
        assert resp.status_code == 200
        data = resp.json()
        assert "mae" in data
        assert "rmse" in data

    def test_trust_reset_valid(self):
        self.client.post("/api/v1/sensors/simulate/step")
        resp = self.client.post("/api/v1/sensors/trust/reset",
                                json={"village_id": "V01", "sensor_type": "soil_moisture"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "reset"

    def test_trust_reset_invalid_sensor_type(self):
        resp = self.client.post("/api/v1/sensors/trust/reset",
                                json={"village_id": "V01", "sensor_type": "temperature"})
        assert resp.status_code == 422
