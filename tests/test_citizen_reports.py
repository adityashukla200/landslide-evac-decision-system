"""Unit and integration tests for citizen ground-truth reports:
media validation, EXIF extraction/stripping, rate limiting, nearest-village mapping,
and officer verification.
"""

import io
import pytest
from datetime import datetime, timezone
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.citizen_reports import (
    reset_rate_limits,
    find_nearest_village,
    haversine_km,
    strip_image_exif,
    MAX_PHOTO_SIZE,
)
from backend.app.db.session import SessionLocal
from backend.app.db.models import Village, CitizenReport


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Reset rate limiters between tests."""
    reset_rate_limits()


def create_test_image(size=(120, 120), color="blue", with_gps=False) -> bytes:
    """Helper to generate in-memory JPEG bytes, optionally with EXIF GPS tags."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()

    if with_gps:
        # Pillow EXIF with GPS IFD
        exif = img.getexif()
        gps_ifd = exif.get_ifd(0x8825)
        # Lat: 30 deg 44 min 0 sec N = 30.7333
        gps_ifd[1] = "N"
        gps_ifd[2] = (30.0, 44.0, 0.0)
        # Lon: 78 deg 26 min 0 sec E = 78.4333
        gps_ifd[3] = "E"
        gps_ifd[4] = (78.0, 26.0, 0.0)
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")

    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Upload & Media Validation
# ---------------------------------------------------------------------------

def test_upload_valid_photo(client):
    """Test valid photo upload with coordinates and reported_flood=True."""
    img_bytes = create_test_image(color="red")
    resp = client.post(
        "/api/v1/reports/citizen",
        data={
            "latitude": 30.732,
            "longitude": 78.441,
            "accuracy_meters": 12.5,
            "reported_flood": "true",
            "caption": "Boulders on road near bridge",
            "reporter_phone": "+919876543210",
        },
        files={"file": ("debris_slope.jpg", img_bytes, "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["media_type"] == "photo"
    assert data["reported_flood"] is True
    assert data["report_id"].startswith("CR_")
    assert data["media_url"] == f"/api/v1/reports/{data['report_id']}/media"
    assert data["thumbnail_url"] is not None


def test_upload_valid_video(client):
    """Test valid MP4 video upload."""
    # Construct minimal MP4 header bytes
    mock_mp4_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42\x00\x00\x00\x08free"
    resp = client.post(
        "/api/v1/reports/citizen",
        data={
            "latitude": 30.932,
            "longitude": 78.468,
            "reported_flood": "false",
            "caption": "No water accumulation here, false alarm.",
        },
        files={"file": ("stream_video.mp4", mock_mp4_bytes, "video/mp4")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["media_type"] == "video"
    assert data["reported_flood"] is False
    assert data["report_id"].startswith("CR_")


def test_upload_invalid_file_type_rejected(client):
    """Verify that unsupported file extensions are rejected with HTTP 400."""
    resp = client.post(
        "/api/v1/reports/citizen",
        data={"latitude": 30.73, "longitude": 78.44, "reported_flood": "true"},
        files={"file": ("malicious_payload.exe", b"MZ\x90\x00binary", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_upload_file_size_exceeded(client):
    """Verify that files exceeding the size limit (20MB photo) are rejected."""
    oversized = b"0" * (MAX_PHOTO_SIZE + 1024)
    resp = client.post(
        "/api/v1/reports/citizen",
        data={"latitude": 30.73, "longitude": 78.44, "reported_flood": "true"},
        files={"file": ("huge_photo.jpg", oversized, "image/jpeg")},
    )
    assert resp.status_code == 413
    assert "exceeds maximum allowed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 2. EXIF Coordinates Extraction & Privacy Stripping
# ---------------------------------------------------------------------------

def test_exif_gps_extraction_when_lat_lon_omitted(client):
    """If client omits lat/lon form fields, GPS should be extracted from EXIF."""
    gps_photo = create_test_image(with_gps=True)
    resp = client.post(
        "/api/v1/reports/citizen",
        data={"reported_flood": "true", "caption": "Photo with camera GPS"},
        files={"file": ("camera_photo.jpg", gps_photo, "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    # 30 deg 44 min = 30.7333, 78 deg 26 min = 78.4333
    assert abs(data["latitude"] - 30.7333) < 0.01
    assert abs(data["longitude"] - 78.4333) < 0.01


def test_missing_coordinates_rejected_if_no_exif(client):
    """Reject upload if no coordinates provided in form AND no EXIF GPS present."""
    plain_photo = create_test_image(with_gps=False)
    resp = client.post(
        "/api/v1/reports/citizen",
        data={"reported_flood": "true"},
        files={"file": ("no_gps.jpg", plain_photo, "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "Geographic coordinates required" in resp.json()["detail"]


def test_exif_is_stripped_for_privacy(client):
    """Verify that saved media on disk has all EXIF stripped to protect citizen privacy."""
    gps_photo = create_test_image(with_gps=True)
    resp = client.post(
        "/api/v1/reports/citizen",
        data={"reported_flood": "true"},
        files={"file": ("privacy_test.jpg", gps_photo, "image/jpeg")},
    )
    assert resp.status_code == 201
    report_id = resp.json()["report_id"]

    # Stream the file back
    media_resp = client.get(f"/api/v1/reports/{report_id}/media")
    assert media_resp.status_code == 200

    # Parse streamed bytes and verify zero EXIF
    downloaded_img = Image.open(io.BytesIO(media_resp.content))
    exif_keys = list(downloaded_img.getexif().keys())
    assert len(exif_keys) == 0, f"Expected 0 EXIF tags, found: {exif_keys}"


# ---------------------------------------------------------------------------
# 3. Nearest Village Mapping
# ---------------------------------------------------------------------------

def test_nearest_village_mapping_in_range(client):
    """Coordinates close to Bhatwari (30.932, 78.468) should map to nearest village."""
    img_bytes = create_test_image()
    resp = client.post(
        "/api/v1/reports/citizen",
        data={
            "latitude": 30.816,
            "longitude": 78.620,
            "reported_flood": "true",
        },
        files={"file": ("bhatwari_slope.jpg", img_bytes, "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["village_id"] is not None
    assert data["distance_from_village_km"] < 2.0


def test_nearest_village_mapping_out_of_range(client):
    """Coordinates far outside district (>25km) should map village_id to None."""
    img_bytes = create_test_image()
    resp = client.post(
        "/api/v1/reports/citizen",
        data={
            "latitude": 28.6139,  # New Delhi
            "longitude": 77.2090,
            "reported_flood": "false",
        },
        files={"file": ("far_photo.jpg", img_bytes, "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["village_id"] is None


# ---------------------------------------------------------------------------
# 4. Rate Limiting (Abuse Protection)
# ---------------------------------------------------------------------------

def test_rate_limiting_enforces_max_5_reports(client):
    """Enforce max 5 reports per 15 minutes by IP."""
    img_bytes = create_test_image()
    # 5 successful submissions
    for i in range(5):
        r = client.post(
            "/api/v1/reports/citizen",
            data={"latitude": 30.73, "longitude": 78.44, "reported_flood": "true"},
            files={"file": (f"burst_{i}.jpg", img_bytes, "image/jpeg")},
        )
        assert r.status_code == 201

    # 6th submission should be rejected with 429
    burst_fail = client.post(
        "/api/v1/reports/citizen",
        data={"latitude": 30.73, "longitude": 78.44, "reported_flood": "true"},
        files={"file": ("burst_6.jpg", img_bytes, "image/jpeg")},
    )
    assert burst_fail.status_code == 429
    assert "Rate limit exceeded" in burst_fail.json()["detail"]


# ---------------------------------------------------------------------------
# 5. Dashboard Listing, Streaming & Officer Verification
# ---------------------------------------------------------------------------

def test_list_reports_and_filters(client):
    """Test listing reports with village and status filters."""
    # List reports
    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200
    reports = resp.json()
    assert isinstance(reports, list)
    assert len(reports) > 0

    first = reports[0]
    assert "id" in first
    assert "media_url" in first
    assert "status" in first
    assert "reported_flood" in first

    # Filter by status
    pending_resp = client.get("/api/v1/reports?status=pending")
    assert pending_resp.status_code == 200
    assert all(r["status"] == "pending" for r in pending_resp.json())


def test_officer_status_update_and_audit(client):
    """Officer marks report verified with audit trail."""
    img_bytes = create_test_image()
    sub_resp = client.post(
        "/api/v1/reports/citizen",
        data={
            "latitude": 30.73,
            "longitude": 78.44,
            "reported_flood": "true",
            "caption": "Flooding near market",
            "reporter_phone": "+919876543210",
        },
        files={"file": ("verify_test.jpg", img_bytes, "image/jpeg")},
    )
    assert sub_resp.status_code == 201
    report_id = sub_resp.json()["report_id"]

    # Officer marks verified
    put_resp = client.put(
        f"/api/v1/reports/{report_id}/status",
        json={
            "status": "verified",
            "reviewed_by": "Cmdt. R.K. Bhardwaj (NDRF)",
            "notes": "Verified by QRT team on site.",
        },
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["new_status"] == "verified"
    assert data["reviewed_by"] == "Cmdt. R.K. Bhardwaj (NDRF)"

    # Verify audit log contains entry
    audit = data["audit_log"]
    assert any(
        a.get("new_status") == "verified" and a.get("changed_by") == "Cmdt. R.K. Bhardwaj (NDRF)"
        for a in audit
    )

    # Check updated report via GET
    get_resp = client.get(f"/api/v1/reports?status=verified")
    assert any(r["id"] == report_id and r["status"] == "verified" for r in get_resp.json())


def test_media_and_thumbnail_streaming(client):
    """Test streaming media and thumbnail files via GET /reports/{id}/media."""
    img_bytes = create_test_image(color="green")
    sub_resp = client.post(
        "/api/v1/reports/citizen",
        data={"latitude": 30.73, "longitude": 78.44, "reported_flood": "true"},
        files={"file": ("stream_test.jpg", img_bytes, "image/jpeg")},
    )
    report_id = sub_resp.json()["report_id"]

    # Stream media
    media_resp = client.get(f"/api/v1/reports/{report_id}/media")
    assert media_resp.status_code == 200
    assert len(media_resp.content) > 0
    assert media_resp.headers["content-type"] == "image/jpeg"

    # Stream thumbnail
    thumb_resp = client.get(f"/api/v1/reports/{report_id}/thumbnail")
    assert thumb_resp.status_code == 200
    assert len(thumb_resp.content) > 0
