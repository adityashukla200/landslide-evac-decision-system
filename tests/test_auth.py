"""Unit and integration tests for Officer Authentication, JWT, RBAC, and Rate Limiting."""

import time
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Officer, CitizenReport
from backend.app.db.seeds_officers import seed_officers
from backend.app.core.security import (
    create_access_token,
    LOGIN_ATTEMPTS,
    hash_password,
)


@pytest.fixture(scope="module", autouse=True)
def setup_officers_db():
    """Ensure demo officers are seeded in database before running tests."""
    seed_officers()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Login Authentication Tests
# ---------------------------------------------------------------------------

def test_officer_login_success_with_email(client):
    """Successful login using official email and demo password."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ddmo.uttarkashi@uk.gov.in", "password": "Uttarkashi@2026"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800
    assert data["officer"]["email"] == "ddmo.uttarkashi@uk.gov.in"
    assert data["officer"]["role"] == "admin"
    assert data["officer"]["district"] == "Uttarkashi"
    # Verify refresh token cookie is set
    assert "refresh_token" in resp.cookies


def test_officer_login_success_with_phone(client):
    """Successful login using official phone number and demo password."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "+919412022002", "password": "NDRF#Rescue2026"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["officer"]["name"] == "Maj. Vikram Negi"
    assert data["officer"]["role"] == "officer"


def test_officer_login_invalid_password(client):
    """Invalid password returns 401 Unauthorized."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ddmo.uttarkashi@uk.gov.in", "password": "WrongPassword999!"},
    )
    assert resp.status_code == 401
    assert "Invalid email/phone or password" in resp.json()["detail"]


def test_officer_login_nonexistent_user(client):
    """Non-existent username returns 401 Unauthorized."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "fake.user@nowhere.com", "password": "SomePassword123"},
    )
    assert resp.status_code == 401
    assert "Invalid email/phone or password" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 2. Rate Limiting Tests
# ---------------------------------------------------------------------------

def test_login_rate_limiting_enforcement(client):
    """Max 5 failed attempts triggers 429 Too Many Requests."""
    target_user = "rate_limit_test@uk.gov.in"
    
    # 5 failed attempts
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": target_user, "password": "BadPassword"},
        )
        assert resp.status_code == 401

    # 6th attempt must be rejected with 429
    blocked_resp = client.post(
        "/api/v1/auth/login",
        json={"username": target_user, "password": "BadPassword"},
    )
    assert blocked_resp.status_code == 429
    assert "Too many failed login attempts" in blocked_resp.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Refresh Token & Logout Tests
# ---------------------------------------------------------------------------

def test_refresh_token_endpoint(client):
    """Valid refresh token issues a new access token."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "bdo.bhatwari@uk.gov.in", "password": "Bhatwari@2026"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Call /refresh with token in JSON payload
    ref_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_resp.status_code == 200
    data = ref_resp.json()
    assert "access_token" in data
    assert data["officer"]["email"] == "bdo.bhatwari@uk.gov.in"


def test_logout_endpoint(client):
    """Logout endpoint successfully invalidates session cookie."""
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


# ---------------------------------------------------------------------------
# 4. Protected Endpoints: JWT Validation, Expiry & Role Checks
# ---------------------------------------------------------------------------

def test_protected_endpoint_rejects_missing_token(client):
    """Calling protected officer endpoint with no token returns 401."""
    resp = client.put(
        "/api/v1/thresholds/VIL_UTK_01",
        json={"watch_threshold": 0.015, "warning_threshold": 0.030, "evacuate_threshold": 0.150},
    )
    assert resp.status_code == 401
    assert "Officer authentication required" in resp.json()["detail"]


def test_protected_endpoint_rejects_invalid_token(client):
    """Calling protected endpoint with malformed/forged token returns 401."""
    headers = {"Authorization": "Bearer totally_forged_invalid_jwt_token"}
    resp = client.put(
        "/api/v1/thresholds/VIL_UTK_01",
        json={"watch_threshold": 0.015, "warning_threshold": 0.030, "evacuate_threshold": 0.150},
        headers=headers,
    )
    assert resp.status_code == 401


def test_protected_endpoint_rejects_expired_token(client):
    """Calling protected endpoint with an expired token returns 401."""
    # Create expired token (-10 minutes)
    expired_token = create_access_token(
        {"sub": "OFF_DDMO_UTK_01", "role": "admin", "name": "Dr. Rajesh Sharma"},
        expires_delta=timedelta(minutes=-10),
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    resp = client.put(
        "/api/v1/thresholds/VIL_UTK_01",
        json={"watch_threshold": 0.015, "warning_threshold": 0.030, "evacuate_threshold": 0.150},
        headers=headers,
    )
    assert resp.status_code == 401
    assert "Token has expired" in resp.json()["detail"]


def test_protected_endpoint_permits_valid_token(client):
    """Calling protected endpoint with valid JWT token succeeds with 200."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "ddmo.uttarkashi@uk.gov.in", "password": "Uttarkashi@2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/api/v1/thresholds/VIL_UTK_01",
        json={
            "watch_threshold": 0.012,
            "warning_threshold": 0.024,
            "evacuate_threshold": 0.155,
            "modified_by": "district_official",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["watch_threshold"] == 0.012
    # Verify modified_by was automatically set to officer's name
    assert data["last_modified_by"] == "Dr. Rajesh Sharma"


def test_auth_me_endpoint_with_valid_token(client):
    """GET /api/v1/auth/me returns current officer's profile."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "bdo.bhatwari@uk.gov.in", "password": "Bhatwari@2026"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me = me_resp.json()
    assert me["name"] == "Pooja Rawat"
    assert me["role"] == "officer"
    assert me["district"] == "Uttarkashi"
