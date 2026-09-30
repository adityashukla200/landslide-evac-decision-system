"""Integration and unit tests for multi-channel alerting, CAP 1.2 XML, ladder escalation, and fatigue control."""

import asyncio
import uuid
import xml.etree.ElementTree as ET
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.db.models import Alert, Village, Recipient, AlertDelivery, CommunityReport
from backend.app.services.alerting import (
    CellBroadcastMock,
    SMSMock,
    WhatsAppMock,
    IVRMock,
    VolunteerTaskAdapter,
    SirenMock,
    get_channel_adapter,
    generate_cap_12_xml,
    check_alert_suppression,
    filter_recipients_by_safety,
    AlertLadderOrchestrator,
    calculate_alert_reach,
    calculate_drill_report,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def db_session():
    """Database session fixture."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


from backend.app.core.security import create_access_token
from backend.app.db.seeds_officers import seed_officers


@pytest.fixture(scope="module")
def auth_headers(db_session):
    seed_officers()
    token = create_access_token({"sub": "ddmo.uttarkashi@uk.gov.in", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def setup_village(db_session):
    """Retrieve existing pilot village with pre-seeded recipients."""
    village = db_session.query(Village).filter(Village.id == "VIL_UTK_01").first()
    assert village is not None, "Pilot village VIL_UTK_01 must be pre-seeded in database."
    return village


# ---------------------------------------------------------------------------
# 1. CHANNEL ADAPTERS TESTS
# ---------------------------------------------------------------------------

def test_channel_adapters_common_interface(setup_village, db_session):
    """Verify all 6 channel adapters adhere to common async interface and return DeliveryResult."""
    async def _run():
        rec = db_session.query(Recipient).filter(Recipient.village_id == setup_village.id).first()
        alert = Alert(
            id="ALT_ADAPTER_TEST",
            village_id=setup_village.id,
            tier="WARNING",
            message="Test alert message",
            created_at=datetime.now(timezone.utc),
        )

        adapters = [
            CellBroadcastMock(failure_rate=0.0),
            SMSMock(failure_rate=0.0),
            WhatsAppMock(failure_rate=0.0),
            IVRMock(failure_rate=0.0),
            VolunteerTaskAdapter(failure_rate=0.0),
            SirenMock(failure_rate=0.0),
        ]

        for adapter in adapters:
            assert isinstance(adapter.channel_name, str)
            result = await adapter.send(recipient=rec, alert=alert, message_text=alert.message)
            assert result.success is True
            assert result.status == "SENT"
            assert result.channel == adapter.channel_name
            assert result.recipient_id == rec.id
            assert result.latency_ms >= 0.0

    asyncio.run(_run())


def test_channel_adapter_simulated_failures(setup_village, db_session):
    """Verify adapters correctly handle and report simulated delivery failures."""
    async def _run():
        rec = db_session.query(Recipient).filter(Recipient.village_id == setup_village.id).first()
        alert = Alert(id="ALT_FAIL_TEST", village_id=setup_village.id, tier="EVACUATE", message="Run")

        failing_adapter = SMSMock(failure_rate=1.0)
        result = await failing_adapter.send(recipient=rec, alert=alert, message_text=alert.message)
        assert result.success is False
        assert result.status == "FAILED"
        assert result.error is not None

    asyncio.run(_run())


def test_channel_adapter_factory():
    """Verify channel adapter factory creates instances and handles config."""
    adapter = get_channel_adapter("CELL_BROADCAST", failure_rate=0.05)
    assert isinstance(adapter, CellBroadcastMock)
    assert adapter.failure_rate == 0.05

    siren = get_channel_adapter("SIREN")
    assert isinstance(siren, SirenMock)

    with pytest.raises(ValueError):
        get_channel_adapter("TELEPATHY")


# ---------------------------------------------------------------------------
# 2. CAP 1.2 XML GENERATION TESTS
# ---------------------------------------------------------------------------

def test_cap_12_xml_generation(setup_village):
    """Verify OASIS CAP 1.2 standard XML structure, coordinates polygon, and fields."""
    alert = Alert(
        id="ALT_CAP_001",
        village_id=setup_village.id,
        tier="EVACUATE",
        message="Leave now. Move to high ground immediately.",
        drill_flag=False,
        created_at=datetime.now(timezone.utc),
    )

    xml_str = generate_cap_12_xml(alert, setup_village, is_drill=False)
    assert xml_str.startswith("<?xml")

    root = ET.fromstring(xml_str)
    assert "alert" in root.tag

    # Check fields in root
    identifier = root.find("{urn:oasis:names:tc:emergency:cap:1.2}identifier")
    status = root.find("{urn:oasis:names:tc:emergency:cap:1.2}status")
    scope = root.find("{urn:oasis:names:tc:emergency:cap:1.2}scope")
    info = root.find("{urn:oasis:names:tc:emergency:cap:1.2}info")

    assert identifier is not None and "ALT_CAP_001" in identifier.text
    assert status is not None and status.text == "Actual"
    assert scope is not None and scope.text == "Public"
    assert info is not None

    urgency = info.find("{urn:oasis:names:tc:emergency:cap:1.2}urgency")
    severity = info.find("{urn:oasis:names:tc:emergency:cap:1.2}severity")
    headline = info.find("{urn:oasis:names:tc:emergency:cap:1.2}headline")
    area = info.find("{urn:oasis:names:tc:emergency:cap:1.2}area")

    assert urgency.text == "Immediate"
    assert severity.text == "Extreme"
    assert "EVACUATE DIRECTIVE" in headline.text
    assert area is not None

    polygon = area.find("{urn:oasis:names:tc:emergency:cap:1.2}polygon")
    assert polygon is not None
    coords = polygon.text.strip().split()
    assert len(coords) == 5  # Closed 4-corner bounding box


def test_cap_12_drill_xml(setup_village):
    """Verify CAP 1.2 XML for drill/exercise alerts has status='Test' and headline prefix."""
    alert = Alert(
        id="ALT_CAP_DRILL",
        village_id=setup_village.id,
        tier="WARNING",
        message="Evacuation drill in progress.",
        drill_flag=True,
    )
    xml_str = generate_cap_12_xml(alert, setup_village, is_drill=True)
    root = ET.fromstring(xml_str)
    status = root.find("{urn:oasis:names:tc:emergency:cap:1.2}status")
    assert status.text == "Test"

    info = root.find("{urn:oasis:names:tc:emergency:cap:1.2}info")
    headline = info.find("{urn:oasis:names:tc:emergency:cap:1.2}headline")
    assert "[EXERCISE / DRILL]" in headline.text


# ---------------------------------------------------------------------------
# 3. ALERT FATIGUE CONTROL & SAFE-ZONE FILTERING
# ---------------------------------------------------------------------------

def test_alert_fatigue_suppression(setup_village, db_session):
    """Verify same-tier alert within cooldown is suppressed, but higher tier overrides."""
    db_session.query(AlertDelivery).filter(
        AlertDelivery.alert_id.in_(
            db_session.query(Alert.id).filter(Alert.village_id == setup_village.id)
        )
    ).delete(synchronize_session=False)
    db_session.query(Alert).filter(Alert.village_id == setup_village.id).delete(synchronize_session=False)
    db_session.commit()

    now = datetime.now(timezone.utc)
    base_alert = Alert(
        id=f"ALT_FATIGUE_{uuid.uuid4().hex[:8]}",
        village_id=setup_village.id,
        tier="WATCH",
        message="Heavy clouds detected.",
        created_at=now - timedelta(minutes=10),
        cooldown_until=now + timedelta(minutes=50),
    )
    db_session.add(base_alert)
    db_session.commit()

    # 1. Same tier (WATCH) within cooldown -> SUPPRESSED
    is_suppressed, reason = check_alert_suppression(
        village_id=setup_village.id,
        new_tier="WATCH",
        db=db_session,
        cooldown_minutes=60,
        current_time=now,
    )
    assert is_suppressed is True
    assert "cooldown" in reason.lower()

    # 2. Lower or equal tier (WATCH / GREEN) -> SUPPRESSED
    is_suppressed, _ = check_alert_suppression(
        village_id=setup_village.id,
        new_tier="GREEN",
        db=db_session,
        cooldown_minutes=60,
        current_time=now,
    )
    assert is_suppressed is True

    # 3. Escalation to higher tier (WARNING / EVACUATE) -> ALLOWED (override)
    is_suppressed, reason = check_alert_suppression(
        village_id=setup_village.id,
        new_tier="EVACUATE",
        db=db_session,
        cooldown_minutes=60,
        current_time=now,
    )
    assert is_suppressed is False
    assert reason is None

    # 4. Same tier after cooldown expiration -> ALLOWED
    future_time = now + timedelta(minutes=70)
    is_suppressed, _ = check_alert_suppression(
        village_id=setup_village.id,
        new_tier="WATCH",
        db=db_session,
        cooldown_minutes=60,
        current_time=future_time,
    )
    assert is_suppressed is False


def test_safe_zone_filtering(setup_village, db_session):
    """Verify confirmed-safe citizens or recent acks are excluded from broadcast list."""
    recipients = db_session.query(Recipient).filter(Recipient.village_id == setup_village.id).all()
    assert len(recipients) >= 2

    # Mark one recipient as confirmed safe explicitly
    safe_ids = {recipients[0].id}
    eligible = filter_recipients_by_safety(
        recipients=recipients,
        village_id=setup_village.id,
        db=db_session,
        confirmed_safe_ids=safe_ids,
    )
    assert len(eligible) == len(recipients) - 1
    assert all(r.id not in safe_ids for r in eligible)


# ---------------------------------------------------------------------------
# 4. FALLBACK LADDER ORCHESTRATOR & ACK TESTS
# ---------------------------------------------------------------------------

def test_alert_ladder_orchestration(setup_village, db_session):
    """Verify multi-channel ladder executes and logs every delivery step to DB."""
    async def _run():
        recipients = db_session.query(Recipient).filter(Recipient.village_id == setup_village.id).all()
        alert_id = f"ALT_LADDER_{uuid.uuid4().hex[:8]}"
        alert = Alert(
            id=alert_id,
            village_id=setup_village.id,
            tier="EVACUATE",
            message="Critical threat: Evacuate immediately to shelter.",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(alert)
        db_session.commit()

        # Create orchestrator with 0 failure rate for testing
        orchestrator = AlertLadderOrchestrator(
            failure_rates={"CELL_BROADCAST": 0.0, "SMS": 0.0, "IVR": 0.0, "VOLUNTEER": 0.0, "SIREN": 0.0}
        )

        # Simulate first recipient auto-acknowledging
        result = await orchestrator.execute_alert_ladder(
            alert_id=alert.id,
            db=db_session,
            escalation_window_sec=0.01,
            auto_ack_recipients={recipients[0].id},
        )

        assert result["status"] == "COMPLETED"
        assert result["eligible_recipients"] >= 2
        assert result["deliveries_count"] > 0

        # Verify rows in DB alert_deliveries
        deliveries = db_session.query(AlertDelivery).filter(AlertDelivery.alert_id == alert.id).all()
        channels = {d.channel for d in deliveries}
        assert "CELL_BROADCAST" in channels
        assert "SMS" in channels
        assert "SIREN" in channels  # Because tier is EVACUATE and unacked residents existed

    asyncio.run(_run())


def test_ack_tracking_and_metrics(setup_village, db_session):
    """Verify live reach percentage, channel breakdown, and vulnerable reach calculation."""
    recipients = db_session.query(Recipient).filter(Recipient.village_id == setup_village.id).all()
    # Seed an alert with known deliveries
    alert_id = f"ALT_METRICS_{uuid.uuid4().hex[:8]}"
    alert = Alert(
        id=alert_id,
        village_id=setup_village.id,
        tier="WARNING",
        message="Warning directive",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(alert)

    # Deliveries: 2 sent via SMS, 1 acknowledged
    d1_id = f"DEL_M1_{uuid.uuid4().hex[:6]}"
    d2_id = f"DEL_M2_{uuid.uuid4().hex[:6]}"
    d1 = AlertDelivery(
        id=d1_id,
        alert_id=alert_id,
        recipient_id=recipients[0].id,
        channel="SMS",
        status="SENT",
        sent_at=datetime.now(timezone.utc),
    )
    d2 = AlertDelivery(
        id=d2_id,
        alert_id=alert_id,
        recipient_id=recipients[1].id,
        channel="SMS",
        status="SENT",
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add_all([d1, d2])
    db_session.commit()

    # Acknowledge d2
    AlertLadderOrchestrator.acknowledge_delivery(d2_id, db_session)

    # Compute reach
    reach = calculate_alert_reach(alert_id, db_session)
    assert reach["alert_id"] == alert_id
    assert reach["summary"]["total_reached"] >= 2
    assert reach["summary"]["total_acknowledged"] >= 1
    assert reach["summary"]["reach_percentage"] > 0.0
    assert "SMS" in reach["channels"]


# ---------------------------------------------------------------------------
# 5. FASTAPI API INTEGRATION TESTS
# ---------------------------------------------------------------------------

def test_api_trigger_and_reach_flow(client, setup_village, db_session, auth_headers):
    """Integration test: trigger alert -> get CAP XML -> acknowledge -> get reach metrics."""
    recipients = db_session.query(Recipient).filter(Recipient.village_id == setup_village.id).all()
    # 1. Trigger Alert
    resp = client.post(
        "/api/alerts/trigger",
        json={
            "village_id": setup_village.id,
            "tier": "EVACUATE",
            "message": "Leave immediately. River levels rising.",
            "override_cooldown": True,
            "escalation_window_sec": 0.01,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DISPATCHED"
    alert_id = data["alert_id"]

    # 2. Get CAP 1.2 XML
    cap_resp = client.get(f"/api/alerts/{alert_id}/cap")
    assert cap_resp.status_code == 200
    assert "urn:oasis:names:tc:emergency:cap:1.2" in cap_resp.text

    # 3. Acknowledge Alert by Recipient
    ack_resp = client.post(
        "/api/alerts/ack",
        json={
            "alert_id": alert_id,
            "recipient_id": recipients[0].id,
        },
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # 4. Check Reach Percentage
    reach_resp = client.get(f"/api/alerts/{alert_id}/reach")
    assert reach_resp.status_code == 200
    reach_data = reach_resp.json()
    assert reach_data["summary"]["total_reached"] > 0
    assert reach_data["summary"]["reach_percentage"] > 0


def test_api_community_reports_and_vetting(client, setup_village, auth_headers):
    """Integration test: submit community hazard observation -> list -> review as ground truth."""
    # 1. Submit report
    rep_resp = client.post(
        "/api/reports",
        json={
            "village_id": setup_village.id,
            "lat": 30.7312,
            "lon": 78.4415,
            "photo_url": "https://storage.example.org/debris_chute_01.jpg",
            "text": "Boulders tumbling down slopes near temple road after heavy burst.",
            "reporter_name": "Ramesh Singh",
            "reporter_phone": "+919876543299",
        },
    )
    assert rep_resp.status_code == 201
    rep_data = rep_resp.json()
    assert rep_data["status"] == "SUBMITTED"
    report_id = rep_data["report_id"]

    # 2. List reports
    list_resp = client.get(f"/api/reports?village_id={setup_village.id}")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert any(r["id"] == report_id for r in reports)

    # 3. Review report
    rev_resp = client.put(
        f"/api/reports/{report_id}/review",
        json={
            "status": "VERIFIED",
            "reviewed_by": "NDRF_OFFICER_04",
            "review_notes": "Ground inspection confirmed 40m debris slide.",
            "is_ground_truth_candidate": True,
        },
        headers=auth_headers,
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["review_status"] == "VERIFIED"
    assert rev_data["is_ground_truth_candidate"] is True


def test_api_drill_mode(client, setup_village, auth_headers):
    """Integration test: trigger exercise drill -> inspect drill participation report."""
    resp = client.post(
        "/api/drills/trigger",
        json={
            "village_id": setup_village.id,
            "tier": "WARNING",
            "message": "Community monsoon preparedness exercise.",
            "override_cooldown": True,
            "escalation_window_sec": 0.01,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    drill_id = resp.json()["alert_id"]
    assert resp.json()["is_drill"] is True

    # Check drill report
    report_resp = client.get(f"/api/drills/{drill_id}/report")
    assert report_resp.status_code == 200
    r_data = report_resp.json()
    assert r_data["is_drill"] is True
    assert r_data["exercise_type"] == "COMMUNITY_EVACUATION_DRILL"
    assert "compliance_rating" in r_data
