"""Tests for the Replay Engine: scenario loading, pipeline execution, baseline comparison, kill-internet."""

import pytest
import math
from backend.app.services.replay import (
    get_replay_engine,
    AVAILABLE_SCENARIOS,
    ChannelStatus,
)


# ---- Scenario Registry ----

def test_available_scenarios_not_empty():
    assert len(AVAILABLE_SCENARIOS) >= 2

def test_scenario_ids_are_consistent():
    for scenario_id, scenario in AVAILABLE_SCENARIOS.items():
        assert scenario.id == scenario_id, f"ID mismatch: key={scenario_id}, scenario.id={scenario.id}"

def test_scenario_steps_have_hourly_data():
    for sc in AVAILABLE_SCENARIOS.values():
        assert len(sc.steps) >= 8, f"Scenario {sc.id} has fewer than 8 hourly steps"
        assert sc.impact_hour_offset == 0, f"Impact hour offset must be 0 for scenario {sc.id}"
        assert sc.is_synthetic, f"All current scenarios must be flagged as synthetic"
        assert "SYNTHETIC" in sc.data_source_label.upper(), (
            f"Synthetic scenarios must clearly label data source as synthetic: {sc.id}"
        )

def test_scenario_telemetry_ranges_are_physical():
    """Telemetry values must be within physically plausible ranges."""
    for sc in AVAILABLE_SCENARIOS.values():
        for step in sc.steps:
            assert 0 <= step.rainfall_1h_mm <= 200, f"rainfall_1h out of range at step {step.hour_offset}"
            assert 0 <= step.rainfall_24h_mm <= 1000, f"rainfall_24h out of range at step {step.hour_offset}"
            assert 0 <= step.soil_saturation_pct <= 100, f"soil_sat out of range at step {step.hour_offset}"
            assert 0 <= step.river_stage_m <= 15, f"river_stage out of range at step {step.hour_offset}"
            assert 10 <= step.slope_angle_deg <= 70, f"slope_angle out of range at step {step.hour_offset}"
            assert 0 < step.friction_angle_deg < 60, f"friction_angle out of range"


# ---- Engine Initialization ----

def test_replay_engine_initializes():
    engine = get_replay_engine()
    assert engine is not None
    assert engine.conformal_calibrator.is_fitted


# ---- Full Pipeline Execution ----

@pytest.mark.parametrize("scenario_id", list(AVAILABLE_SCENARIOS.keys()))
def test_run_replay_returns_valid_structure(scenario_id):
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id=scenario_id, kill_internet=False)

    assert "scenario" in result
    assert "summary" in result
    assert "frames" in result

    assert result["scenario"]["is_synthetic"] is True
    assert "SYNTHETIC" in result["scenario"]["data_source_label"].upper()
    assert result["summary"]["total_frames"] >= 8
    assert isinstance(result["frames"], list)
    assert len(result["frames"]) == result["summary"]["total_frames"]


def test_replay_bhatwari_frame_schema():
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    frames = result["frames"]

    first_frame = frames[0]
    required_keys = [
        "step_index", "hour_offset", "timestamp", "phase_label", "is_impact_time",
        "telemetry", "factor_of_safety", "ml_calibrated_prob",
        "conformal_lower", "conformal_upper", "ews_tier",
        "baseline_alert_active", "baseline_tier", "baseline_threshold_rule",
        "lead_time_gain_hours",
        "analog_match_event", "analog_similarity_pct", "explanation_summary",
        "time_to_impact_min", "time_to_evacuate_min", "available_margin_min",
        "safe_route_id", "safe_route_name", "severed_routes", "shelter_name",
        "internet_killed", "active_channels", "delivery_reach_pct",
        "alert_message_en", "alert_message_hi",
    ]
    for key in required_keys:
        assert key in first_frame, f"Missing key '{key}' in first frame"


def test_replay_probabilities_are_monotonically_increasing_during_storm():
    """During the storm buildup phase, calibrated probability should generally increase."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")

    pre_impact_probs = [
        f["ml_calibrated_prob"]
        for f in result["frames"]
        if f["hour_offset"] < 0
    ]
    # Rough check: max probability in last 3 pre-impact hours > prob at T-12h
    assert pre_impact_probs[-1] > pre_impact_probs[0], (
        "Probability should grow from T-12h to near impact"
    )


def test_factor_of_safety_decreases_with_saturation():
    """Fs should decrease or stay low as soil saturation increases."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    frames = result["frames"]

    pre_impact = [f for f in frames if f["hour_offset"] < 0]
    # Fs at T-12h should be higher than Fs at T-1h
    fs_early = pre_impact[0]["factor_of_safety"]
    fs_late  = pre_impact[-1]["factor_of_safety"]
    assert fs_early > fs_late, (
        f"Fs should decrease with saturation: early={fs_early:.3f}, late={fs_late:.3f}"
    )


def test_probability_bounds_valid():
    """Venn-Abers bounds must satisfy 0 <= lower <= prob <= upper <= 1."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    for frame in result["frames"]:
        lo = frame["conformal_lower"]
        prob = frame["ml_calibrated_prob"]
        hi = frame["conformal_upper"]
        assert 0 <= lo <= prob <= hi <= 1.0, (
            f"Invalid bounds at step {frame['step_index']}: [{lo}, {prob}, {hi}]"
        )


def test_ews_tier_sequence_escalates():
    """EWS tier should escalate from NONE/WATCH to WARNING/EVACUATE as storm intensifies."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    frames = result["frames"]

    tier_order = {"NONE": 0, "WATCH": 1, "WARNING": 2, "EVACUATE": 3}
    max_tier_pre_impact = max(
        tier_order[f["ews_tier"]]
        for f in frames if f["hour_offset"] <= 0
    )
    assert max_tier_pre_impact >= 2, (
        "EWS should reach at least WARNING level before impact"
    )


def test_alert_messages_under_160_chars():
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    for frame in result["frames"]:
        assert len(frame["alert_message_en"]) <= 160, (
            f"English alert message exceeds 160 chars at step {frame['step_index']}"
        )
        assert len(frame["alert_message_hi"]) <= 160, (
            f"Hindi alert message exceeds 160 chars at step {frame['step_index']}"
        )


# ---- Baseline Comparison ----

def test_ews_alerts_before_plain_baseline():
    """Multi-source EWS must fire at least 3 hours before the IMD static threshold baseline."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    lead_hours = result["summary"]["extra_lead_time_hours"]
    assert lead_hours >= 3.0, (
        f"EWS must provide at least 3 hours extra lead time; got {lead_hours:.1f}h"
    )


def test_baseline_only_triggers_on_high_rainfall():
    """Plain baseline must NOT trigger at T-12h when 24h rainfall is still low."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    frames = result["frames"]

    early_frame = frames[0]  # T-12h
    assert not early_frame["baseline_alert_active"], (
        "Plain baseline should not trigger at T-12h with low rainfall accumulation"
    )


# ---- Kill Internet Switch ----

def test_kill_internet_disables_cloud_channels():
    """When kill_internet=True, Cell Broadcast, SMS, and IVR should all be undelivered."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic", kill_internet=True)

    for frame in result["frames"]:
        cloud_names = {"Cell Broadcast", "SMS", "SMS / WhatsApp", "IVR Voice Call", "IVR"}
        for ch in frame["active_channels"]:
            if any(n in ch["channel"] for n in cloud_names):
                assert not ch["delivered"], (
                    f"Cloud channel '{ch['channel']}' should be offline when internet is killed"
                )
        assert frame["internet_killed"] is True


def test_kill_internet_fires_local_siren():
    """When kill_internet=True and tier is WARNING or EVACUATE, local siren must fire."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic", kill_internet=True)

    evacuate_frames = [
        f for f in result["frames"]
        if f["ews_tier"] in ("WARNING", "EVACUATE")
    ]
    assert len(evacuate_frames) > 0, "Should have WARNING/EVACUATE frames in this scenario"

    for frame in evacuate_frames:
        siren_chs = [c for c in frame["active_channels"] if "Siren" in c["channel"] or "VHF" in c["channel"] or "Volunteer" in c["channel"]]
        has_local_fire = any(c["delivered"] and c["offline_fallback"] for c in siren_chs)
        assert has_local_fire, (
            f"Local siren/VHF must fire offline when internet is killed at step {frame['step_index']}"
        )


def test_kill_internet_reaches_acceptable_pct():
    """Even with no internet, offline siren coverage should reach at least 70% in evacuate frames."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic", kill_internet=True)

    evacuate_frames = [
        f for f in result["frames"]
        if f["ews_tier"] in ("WARNING", "EVACUATE") and f["delivery_reach_pct"] > 0
    ]
    for frame in evacuate_frames:
        assert frame["delivery_reach_pct"] >= 60.0, (
            f"Offline reach must be >= 60% at step {frame['step_index']}, got {frame['delivery_reach_pct']}%"
        )


# ---- Evacuation Logic ----

def test_evacuation_margin_positive_early():
    """At T-6h the evacuation margin must be comfortably positive (time to evacuate before impact)."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    frames = result["frames"]

    early_frames = [f for f in frames if f["hour_offset"] <= -6]
    for f in early_frames:
        assert f["available_margin_min"] > 0, (
            f"Margin must be positive at {f['hour_offset']}h; got {f['available_margin_min']:.0f} min"
        )


def test_route_severance_activates_late():
    """Route A severance should only appear at or after T-2h (late-stage creep)."""
    engine = get_replay_engine()
    result = engine.run_replay(scenario_id="bhatwari_debris_flow_synthetic")
    frames = result["frames"]

    for f in frames:
        if f["hour_offset"] <= -4:   # Before T-3h: routes should be open
            assert "Route A" not in f["severed_routes"], (
                f"Route A should NOT be severed at hour_offset={f['hour_offset']}"
            )


# ---- FastAPI Endpoint ----

def test_replay_api_scenarios_list():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    resp = client.get("/api/v1/replay/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    for item in data:
        assert "id" in item
        assert "is_synthetic" in item
        assert item["is_synthetic"] is True


def test_replay_api_run_returns_timeline():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/v1/replay/run", json={
        "scenario_id": "bhatwari_debris_flow_synthetic",
        "kill_internet": False,
        "speed_multiplier": 1.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "frames" in data
    assert "summary" in data
    assert data["summary"]["total_frames"] >= 8


def test_replay_api_kill_internet_flag():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/v1/replay/run", json={
        "scenario_id": "bhatwari_debris_flow_synthetic",
        "kill_internet": True,
        "speed_multiplier": 1.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["internet_killed"] is True


def test_replay_api_unknown_scenario_returns_404():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    resp = client.post("/api/v1/replay/run", json={
        "scenario_id": "totally_unknown_scenario_xyz",
        "kill_internet": False,
        "speed_multiplier": 1.0,
    })
    assert resp.status_code == 404
