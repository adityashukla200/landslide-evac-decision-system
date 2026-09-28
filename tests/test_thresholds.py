"""Unit tests for Bayes-optimal thresholds, cost formulas, episode merging, and API endpoints."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Village, VillageThreshold
from ml.decision.thresholds import (
    compute_village_costs,
    compute_bayes_optimal_threshold,
    derive_village_thresholds,
    merge_consecutive_alert_episodes,
    evaluate_episode_level,
    MIN_OPERATIONAL_THRESHOLD,
    MAX_OPERATIONAL_THRESHOLD,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


def test_cost_formulas_sensitivity():
    """Verify cost formulas behave monotonically with population, vulnerability, and terrain exposure."""
    base_village = {
        "population": 1000,
        "vulnerable_population": 200,
        "slope": 25.0,
        "distance_to_stream": 100.0,
        "historical_alert_fatigue_rate": 0.20,
        "evacuation_disruption_index": 0.10,
    }
    c_miss_base, c_fa_base = compute_village_costs(base_village)

    # 1. Higher vulnerable population must increase cost_miss
    more_vuln = base_village.copy()
    more_vuln["vulnerable_population"] = 400
    c_miss_vuln, c_fa_vuln = compute_village_costs(more_vuln)
    assert c_miss_vuln > c_miss_base
    assert c_fa_vuln == c_fa_base

    # 2. Steeper slope must increase cost_miss
    steeper = base_village.copy()
    steeper["slope"] = 42.0
    c_miss_slope, _ = compute_village_costs(steeper)
    assert c_miss_slope > c_miss_base

    # 3. Closer to stream must increase cost_miss
    near_stream = base_village.copy()
    near_stream["distance_to_stream"] = 20.0
    c_miss_stream, _ = compute_village_costs(near_stream)
    assert c_miss_stream > c_miss_base

    # 4. Higher fatigue rate and disruption must increase cost_false_alarm
    more_fatigue = base_village.copy()
    more_fatigue["historical_alert_fatigue_rate"] = 0.50
    more_fatigue["evacuation_disruption_index"] = 0.25
    _, c_fa_fatigue = compute_village_costs(more_fatigue)
    assert c_fa_fatigue > c_fa_base


def test_bayes_optimal_threshold_computation_and_clipping():
    """Verify Bayes optimal threshold formula p* = c_fa / (c_fa + c_miss) and clipping bounds."""
    # Standard costs
    c_miss = 4000.0
    c_fa = 100.0
    expected_p = 100.0 / (100.0 + 4000.0)
    p_star = compute_bayes_optimal_threshold(c_miss, c_fa)
    assert abs(p_star - expected_p) < 1e-4

    # Extremely high miss cost -> clipped to min_thresh
    p_clipped_low = compute_bayes_optimal_threshold(cost_miss=1e7, cost_false_alarm=1.0)
    assert p_clipped_low == MIN_OPERATIONAL_THRESHOLD

    # Extremely high false alarm cost -> clipped to max_thresh
    p_clipped_high = compute_bayes_optimal_threshold(cost_miss=1.0, cost_false_alarm=1e7)
    assert p_clipped_high == MAX_OPERATIONAL_THRESHOLD


def test_derive_village_thresholds_hierarchy():
    """Verify derive_village_thresholds produces strictly ordered tiers: watch < warning < evacuate."""
    v_data = {
        "village_id": "VIL_TEST_01",
        "population": 1200,
        "vulnerable_population": 250,
        "slope": 34.0,
        "distance_to_stream": 45.0,
    }
    th = derive_village_thresholds(v_data)

    assert th["village_id"] == "VIL_TEST_01"
    assert th["cost_miss"] > 0
    assert th["cost_false_alarm"] > 0
    assert 0.0 < th["watch_threshold"] < th["warning_threshold"] < th["evacuate_threshold"] <= 1.0


def test_episode_merging_gap_logic():
    """Verify consecutive alert hours with gap <= 6h are merged, and gap > 6h creates new episode."""
    times = pd.date_range("2023-07-01 00:00:00", periods=24, freq="h")
    alert_flags = np.zeros(24, dtype=int)

    # Alerts at 01:00, 03:00, 05:00 (gaps of 2 hours <= 6h) -> Episode 1
    alert_flags[1] = 1
    alert_flags[3] = 1
    alert_flags[5] = 1

    # Alert at 15:00 (gap of 10 hours from 05:00 > 6h) -> Episode 2
    alert_flags[15] = 1

    episodes = merge_consecutive_alert_episodes(times, alert_flags, max_gap_hours=6)
    assert len(episodes) == 2

    # Check episode 1 bounds
    assert episodes[0]["start"] == times[1]
    assert episodes[0]["end"] == times[5]
    assert episodes[0]["window_end"] == times[5] + pd.Timedelta(hours=6)

    # Check episode 2 bounds
    assert episodes[1]["start"] == times[15]
    assert episodes[1]["end"] == times[15]
    assert episodes[1]["window_end"] == times[15] + pd.Timedelta(hours=6)


def test_api_get_thresholds(client):
    """Test GET /api/v1/thresholds/{village_id} endpoint."""
    response = client.get("/api/v1/thresholds/VIL_UTK_01")
    assert response.status_code == 200
    data = response.json()

    assert data["village_id"] == "VIL_UTK_01"
    assert "cost_miss" in data
    assert "cost_false_alarm" in data
    assert "bayes_optimal_threshold" in data
    assert "watch_threshold" in data
    assert "warning_threshold" in data
    assert "evacuate_threshold" in data
    assert 0.0 < data["watch_threshold"] < data["warning_threshold"] < data["evacuate_threshold"]
    assert "audit_log" in data

    # 404 for non-existent village
    resp_404 = client.get("/api/v1/thresholds/NON_EXISTENT_VILLAGE")
    assert resp_404.status_code == 404


def test_api_put_thresholds_validation_and_audit_logging(client):
    """Test PUT /api/v1/thresholds/{village_id} updates values and records audit log."""
    # 1. Valid update
    update_payload = {
        "watch_threshold": 0.0120,
        "warning_threshold": 0.0220,
        "evacuate_threshold": 0.1600,
        "cost_miss": 3500.0,
        "cost_false_alarm": 95.0,
        "max_alerts_per_year": 12,
        "modified_by": "district_magistrate_uttarkashi",
        "change_reason": "Monsoon readiness review adjustment",
    }
    put_resp = client.put("/api/v1/thresholds/VIL_UTK_02", json=update_payload)
    assert put_resp.status_code == 200
    data = put_resp.json()

    assert data["watch_threshold"] == 0.0120
    assert data["warning_threshold"] == 0.0220
    assert data["evacuate_threshold"] == 0.1600
    assert data["max_alerts_per_year"] == 12
    assert data["last_modified_by"] == "district_magistrate_uttarkashi"
    assert len(data["audit_log"]) > 0

    latest_log = data["audit_log"][-1]
    assert latest_log["modified_by"] == "district_magistrate_uttarkashi"
    assert "Monsoon readiness" in latest_log["reason"]
    assert "previous_values" in latest_log

    # 2. Reject hierarchy violation: watch >= warning
    invalid_hierarchy = {
        "watch_threshold": 0.0350,
        "warning_threshold": 0.0200,  # Lower than watch!
        "evacuate_threshold": 0.1500,
        "modified_by": "test_officer",
    }
    bad_resp = client.put("/api/v1/thresholds/VIL_UTK_02", json=invalid_hierarchy)
    assert bad_resp.status_code == 422
    assert "hierarchy" in bad_resp.json()["detail"].lower()

    # 3. Reject negative costs
    invalid_cost = {
        "cost_miss": -50.0,
        "modified_by": "test_officer",
    }
    cost_resp = client.put("/api/v1/thresholds/VIL_UTK_02", json=invalid_cost)
    assert cost_resp.status_code == 422
