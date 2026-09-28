"""Unit tests for RBAC, input validation, rate limiting, and PII masking."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import mask_phone_number, mask_recipient_pii, UserRole, normalize_role


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_normalize_role():
    assert normalize_role("DISTRICT_OFFICER") == UserRole.OFFICER
    assert normalize_role("officer") == UserRole.OFFICER
    assert normalize_role("ndrf_commander") == UserRole.OFFICER
    assert normalize_role("FIELD_VOLUNTEER") == UserRole.VOLUNTEER
    assert normalize_role("volunteer") == UserRole.VOLUNTEER
    assert normalize_role("citizen") == UserRole.CITIZEN
    assert normalize_role(None) == UserRole.CITIZEN
    assert normalize_role("random_guest") == UserRole.CITIZEN


def test_mask_phone_number():
    assert mask_phone_number("+919876543210") == "+919******210"
    assert mask_phone_number("9876543210") == "9876***210"
    assert mask_phone_number("123") == "******"
    assert mask_phone_number("") == ""
    assert mask_phone_number(None) == ""


def test_mask_recipient_pii():
    sample = {
        "id": "REC_01",
        "name": "Sunil Negi",
        "phone": "+919876543210",
        "phone_number": "+919876543210",
        "village_id": "V01",
    }
    sanitized = mask_recipient_pii(sample)
    assert sanitized["phone"] == "+919******210"
    assert sanitized["phone_number"] == "+919******210"
    assert sanitized["name"] == "Sunil Negi"


def test_security_whoami_default(client):
    resp = client.get("/api/v1/security/whoami")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "officer"  # default in local/demo mode
    assert "trigger_emergency_alert" in data["privileges"]


def test_security_whoami_with_role_headers(client):
    # Test volunteer role header
    resp = client.get("/api/v1/security/whoami", headers={"X-User-Role": "volunteer"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "volunteer"
    assert "view_volunteer_tasks" in data["privileges"]

    # Test citizen role header
    resp = client.get("/api/v1/security/whoami", headers={"X-User-Role": "citizen"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "citizen"
    assert "access_tourist_portal" in data["privileges"]


def test_rbac_officer_action_permitted_for_officer(client):
    resp = client.post("/api/v1/security/officer-only-action", headers={"X-User-Role": "officer"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_rbac_officer_action_forbidden_for_volunteer(client):
    resp = client.post("/api/v1/security/officer-only-action", headers={"X-User-Role": "volunteer"})
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_rbac_officer_action_forbidden_for_citizen(client):
    resp = client.post("/api/v1/security/officer-only-action", headers={"X-User-Role": "citizen"})
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_rbac_volunteer_action(client):
    # Officer can do volunteer action (hierarchy)
    resp_off = client.post("/api/v1/security/volunteer-action", headers={"X-User-Role": "officer"})
    assert resp_off.status_code == 200

    # Volunteer can do volunteer action
    resp_vol = client.post("/api/v1/security/volunteer-action", headers={"X-User-Role": "volunteer"})
    assert resp_vol.status_code == 200

    # Citizen is forbidden
    resp_cit = client.post("/api/v1/security/volunteer-action", headers={"X-User-Role": "citizen"})
    assert resp_cit.status_code == 403


def test_rate_limiting_headers_present(client):
    resp = client.get("/api/v1/security/whoami")
    assert resp.status_code == 200
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers
    limit = int(resp.headers["x-ratelimit-limit"])
    assert limit >= 60


def test_input_validation_thresholds(client):
    # Watch threshold out of bounds (> 0.999)
    resp = client.put("/api/v1/thresholds/VIL_UTK_01", json={"watch_threshold": 1.5})
    assert resp.status_code in [404, 422]  # either village not found or 422 invalid payload
