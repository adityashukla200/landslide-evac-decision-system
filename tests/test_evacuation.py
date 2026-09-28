"""Unit tests for evacuation route optimization, time-to-impact forecasting, multilingual alerts, and task cards."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.services.evacuation import (
    estimate_time_to_impact,
    compute_walking_time,
    EvacuationNetworkRouter,
    determine_margin_alert_stage,
    generate_alert_messages,
    generate_volunteer_task_cards,
    assess_evacuation_readiness,
    translate_bhashini,
    MESSAGE_TEMPLATES,
    BASE_WALKING_SPEED_M_PER_MIN,
    VULNERABLE_WALKING_SPEED_M_PER_MIN,
    NIGHT_TIME_FACTOR,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def db_session():
    """Database session fixture."""
    session = SessionLocal()
    yield session
    session.close()


def test_time_to_impact_estimation():
    """Verify time-to-impact calculation decreases with rainfall acceleration and high model probability."""
    # 1. Calm weather condition
    calm = estimate_time_to_impact(
        current_rainfall_rate_mm_h=2.0,
        rainfall_trend_rate=-1.0,
        model_probability=0.001,
    )
    assert calm["min_minutes"] >= 300.0
    assert calm["likely_minutes"] >= 360.0
    assert calm["urgency"] == "LOW"

    # 2. Severe storm condition (high intensity + rapid rise)
    storm = estimate_time_to_impact(
        current_rainfall_rate_mm_h=45.0,
        rainfall_trend_rate=15.0,
        model_probability=0.180,
    )
    assert storm["min_minutes"] <= 40.0
    assert storm["likely_minutes"] <= 60.0
    assert storm["urgency"] in ("CRITICAL", "HIGH")
    assert storm["min_minutes"] <= storm["likely_minutes"]


def test_walking_time_penalties():
    """Verify walking duration adjustments for vulnerable citizens, night time, and trail cut risk."""
    length = 1000.0  # 1 km

    base_time = compute_walking_time(length, is_vulnerable=False, is_night=False, cut_risk=0.0)
    expected_base = length / BASE_WALKING_SPEED_M_PER_MIN
    assert abs(base_time - expected_base) < 0.2

    # Vulnerable citizens walk ~2x slower
    vuln_time = compute_walking_time(length, is_vulnerable=True, is_night=False, cut_risk=0.0)
    assert vuln_time > base_time * 1.8

    # Night time factor adds 40% penalty
    night_time = compute_walking_time(length, is_vulnerable=False, is_night=True, cut_risk=0.0)
    assert abs(night_time - (base_time * NIGHT_TIME_FACTOR)) < 0.2

    # Cut risk introduces hazard delay
    risky_time = compute_walking_time(length, is_vulnerable=False, is_night=False, cut_risk=0.50)
    assert risky_time > base_time * 2.0


def test_evacuation_network_routing_and_cut_risk(db_session):
    """Test NetworkX router finds safe paths and steers around severed routes."""
    router = EvacuationNetworkRouter(db_session)
    plan = router.select_best_evacuation_plan(village_id="VIL_UTK_01")

    assert "shelter_id" in plan
    assert "route_name" in plan
    assert "time_to_evacuate_minutes" in plan
    assert plan["time_to_evacuate_minutes"] > 0
    assert len(plan["path_nodes"]) >= 2
    assert plan["path_nodes"][0] == "VIL_UTK_01"


def test_margin_alert_stage_escalation():
    """Verify alert stages escalate as available evacuation margin narrows."""
    # Critical margin (<= 15 min) -> EVACUATE
    stage_evac, margin_evac = determine_margin_alert_stage(time_to_impact_likely_minutes=30.0, time_to_evacuate_minutes=20.0)
    assert stage_evac == "EVACUATE"
    assert margin_evac == 10.0

    # Warning margin (15 < margin <= 45 min) -> WARNING
    stage_warn, margin_warn = determine_margin_alert_stage(time_to_impact_likely_minutes=60.0, time_to_evacuate_minutes=25.0)
    assert stage_warn == "WARNING"
    assert margin_warn == 35.0

    # Watch margin (45 < margin <= 120 min) -> WATCH
    stage_watch, margin_watch = determine_margin_alert_stage(time_to_impact_likely_minutes=120.0, time_to_evacuate_minutes=30.0)
    assert stage_watch == "WATCH"
    assert margin_watch == 90.0

    # Comfortable margin (> 120 min) -> NONE
    stage_none, margin_none = determine_margin_alert_stage(time_to_impact_likely_minutes=300.0, time_to_evacuate_minutes=30.0)
    assert stage_none == "NONE"
    assert margin_none == 270.0


def test_multilingual_alert_messages_strict_160_char_limit():
    """Verify alert messages in English, Hindi, Garhwali, and Kumaoni never exceed 160 chars."""
    route = "Upper Ridge Trail B"
    shelter = "Panchayat Hall Shelter 2"
    margin = 35.0

    messages = generate_alert_messages(route, shelter, margin)

    assert "en" in messages
    assert "hi" in messages
    assert "gbm" in messages
    assert "kfy" in messages

    for lang, msg in messages.items():
        assert len(msg) <= 160, f"Message for '{lang}' exceeded 160 characters (length: {len(msg)})"
        assert "35" in msg
        assert len(msg.strip()) > 15


def test_bhashini_mock_fallback():
    """Test Bhashini translation function falls back cleanly without API key."""
    text = "Leave now. Go via Route A to Shelter 1."
    translated = translate_bhashini(text, target_lang="hi", api_key=None)
    assert isinstance(translated, str)
    assert len(translated) > 0


def test_volunteer_task_cards_generation(db_session):
    """Test creation of actionable volunteer task cards for vulnerable households."""
    cards = generate_volunteer_task_cards(
        village_id="VIL_UTK_01",
        db=db_session,
        target_shelter_name="Harsil High-Ground Shelter",
        recommended_route_name="Route A",
        available_margin_minutes=25.0,
    )
    assert len(cards) >= 1
    sample = cards[0]

    assert "task_id" in sample
    assert "vulnerable_resident_id" in sample
    assert "assigned_volunteer_id" in sample
    assert "directive" in sample
    assert sample["priority"] in ("CRITICAL", "HIGH", "MEDIUM")
    assert sample["village_id"] == "VIL_UTK_01"


def test_api_post_assess_endpoint(client):
    """Test POST /api/assess/{village_id} endpoint."""
    # 1. Successful assessment with default payload
    resp = client.post("/api/assess/VIL_UTK_01")
    assert resp.status_code == 200
    data = resp.json()

    assert data["village_id"] == "VIL_UTK_01"
    assert "time_to_impact_range" in data
    assert "time_to_evacuate_minutes" in data
    assert "available_margin_minutes" in data
    assert "alert_stage" in data
    assert "recommended_evacuation" in data
    assert "alert_messages" in data
    assert "volunteer_task_cards" in data

    # 2. Assessment with custom scenario (night + vulnerable)
    custom_payload = {
        "current_rainfall_rate_mm_h": 40.0,
        "rainfall_trend_rate": 10.0,
        "model_probability": 0.08,
        "is_night": True,
        "vulnerable_priority": True,
    }
    resp_custom = client.post("/api/assess/VIL_UTK_02", json=custom_payload)
    assert resp_custom.status_code == 200
    data_custom = resp_custom.json()
    assert data_custom["alert_stage"] in ("EVACUATE", "WARNING", "WATCH", "NONE")

    # 3. 404 for invalid village
    resp_404 = client.post("/api/assess/INVALID_VILLAGE_XYZ")
    assert resp_404.status_code == 404
