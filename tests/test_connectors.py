"""Unit tests verifying Open-Meteo connector, 3-layer data source manager, and status endpoint."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import httpx
from fastapi.testclient import TestClient

# Ensure root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app
from backend.app.db.session import SessionLocal
from backend.app.db.models import Observation
from ml.data.connectors.weather import OpenMeteoConnector
from backend.app.services.ingestion.cache import CacheLayer
from backend.app.services.ingestion.manager import DataSourceManager
from backend.app.services.ingestion.scheduler import IngestionScheduler


# Mock Open-Meteo API response payload
MOCK_OPEN_METEO_PAYLOAD = {
    "latitude": 31.03,
    "longitude": 78.74,
    "elevation": 2740.0,
    "hourly": {
        "time": [
            "2026-09-28T12:00",
            "2026-09-28T13:00",
            "2026-09-28T14:00",
        ],
        "precipitation": [0.0, 1.2, 3.4],
        "soil_moisture_0_to_1cm": [0.42, 0.44, 0.47],
    },
}


@pytest.fixture
def mock_client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def isolated_manager():
    """Create isolated DataSourceManager with private in-memory cache for deterministic testing."""
    test_cache = CacheLayer(redis_url="redis://localhost:9999/0", default_ttl=60)
    test_cache.clear()
    return DataSourceManager(cache_backend=test_cache)


def test_weather_connector_success():
    """Test successful Open-Meteo fetch returns LIVE data source and parses coordinates."""
    connector = OpenMeteoConnector(timeout=5.0)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD

    mock_http_client = MagicMock(spec=httpx.Client)
    mock_http_client.get.return_value = mock_resp

    res = connector.fetch_village_weather_sync(
        village_id="VIL_UTK_01",
        lat=31.0367,
        lon=78.7378,
        client=mock_http_client,
    )

    assert res["village_id"] == "VIL_UTK_01"
    assert res["data_source"] == "LIVE"
    assert res["current_precipitation_mm"] == 3.4
    assert res["current_soil_moisture"] == 0.47
    assert len(res["precipitation_mm"]) == 3
    assert res["latency_ms"] >= 0.0


def test_weather_connector_timeout_retry():
    """Test timeout triggers retry and raises error after max attempts."""
    connector = OpenMeteoConnector(timeout=1.0, max_retries=2, backoff_factor=0.01)

    mock_http_client = MagicMock(spec=httpx.Client)
    mock_http_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    with pytest.raises(RuntimeError) as exc_info:
        connector.fetch_village_weather_sync(
            village_id="VIL_UTK_01",
            lat=31.0367,
            lon=78.7378,
            client=mock_http_client,
        )

    assert "after 2 attempts" in str(exc_info.value)
    assert mock_http_client.get.call_count == 2


def test_weather_connector_malformed_response():
    """Test malformed response missing hourly data raises ValueError."""
    connector = OpenMeteoConnector(timeout=1.0, max_retries=1)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": "Invalid format"}

    mock_http_client = MagicMock(spec=httpx.Client)
    mock_http_client.get.return_value = mock_resp

    with pytest.raises(RuntimeError) as exc_info:
        connector.fetch_village_weather_sync(
            village_id="VIL_UTK_01",
            lat=31.0367,
            lon=78.7378,
            client=mock_http_client,
        )

    assert "Malformed Open-Meteo response" in str(exc_info.value)


def test_weather_connector_rate_limiting_429():
    """Test HTTP 429 triggers backoff retry and recovers on subsequent success."""
    connector = OpenMeteoConnector(timeout=1.0, max_retries=3, backoff_factor=0.01)

    mock_resp_429 = MagicMock(spec=httpx.Response)
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"Retry-After": "0.01"}

    mock_resp_200 = MagicMock(spec=httpx.Response)
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = MOCK_OPEN_METEO_PAYLOAD

    mock_http_client = MagicMock(spec=httpx.Client)
    mock_http_client.get.side_effect = [mock_resp_429, mock_resp_200]

    res = connector.fetch_village_weather_sync(
        village_id="VIL_UTK_01",
        lat=31.0367,
        lon=78.7378,
        client=mock_http_client,
    )

    assert res["data_source"] == "LIVE"
    assert mock_http_client.get.call_count == 2


def test_three_layer_fallback_hierarchy(isolated_manager):
    """Verify strict LIVE -> CACHED -> SIMULATED fallback hierarchy and tagging."""
    manager = isolated_manager
    v_id = "VIL_UTK_01"
    lat, lon = 31.0367, 78.7378

    # 1. Fresh state with failing LIVE: must fall back to SIMULATED
    with patch.object(manager.weather_connector, "fetch_village_weather_sync", side_effect=Exception("API down")):
        data1 = manager.get_village_weather(v_id, lat, lon)
        assert data1["data_source"] == "SIMULATED"
        assert manager.source_status["weather"]["state"] == "SIMULATED"

    # 2. Successful LIVE fetch: must tag as LIVE and populate cache
    mock_live = {
        "village_id": v_id,
        "current_precipitation_mm": 5.0,
        "current_soil_moisture": 0.60,
        "times": ["2026-09-28T12:00"],
        "precipitation_mm": [5.0],
        "soil_moisture": [0.60],
        "data_source": "LIVE",
    }
    with patch.object(manager.weather_connector, "fetch_village_weather_sync", return_value=mock_live):
        data2 = manager.get_village_weather(v_id, lat, lon)
        assert data2["data_source"] == "LIVE"
        assert manager.source_status["weather"]["state"] == "LIVE"

    # 3. LIVE fails, but cache is valid: must fall back to CACHED
    with patch.object(manager.weather_connector, "fetch_village_weather_sync", side_effect=Exception("API down")):
        data3 = manager.get_village_weather(v_id, lat, lon)
        assert data3["data_source"] == "CACHED"
        assert manager.source_status["weather"]["state"] == "CACHED"

    # 4. Cache cleared / expired: must fall back to SIMULATED
    manager.cache.clear()
    with patch.object(manager.weather_connector, "fetch_village_weather_sync", side_effect=Exception("API down")):
        data4 = manager.get_village_weather(v_id, lat, lon)
        assert data4["data_source"] == "SIMULATED"
        assert manager.source_status["weather"]["state"] == "SIMULATED"


def test_data_status_endpoint(mock_client):
    """Verify GET /api/v1/data/status returns 200 and schema with source states."""
    response = mock_client.get("/api/v1/data/status")
    assert response.status_code == 200
    data = response.json()

    assert "sources" in data
    assert "timestamp" in data
    sources = data["sources"]
    assert "weather" in sources
    assert "dem" in sources
    assert "soil_moisture" in sources
    assert "landslide_inventory" in sources

    # Verify states are strictly one of LIVE, CACHED, or SIMULATED
    for src_name, info in sources.items():
        assert info["state"] in ["LIVE", "CACHED", "SIMULATED"]


def test_background_scheduler_ingestion_cycle():
    """Verify IngestionScheduler writes valid observations to the database."""
    scheduler = IngestionScheduler(interval_seconds=1800)
    db = SessionLocal()

    mock_weather = {
        "current_precipitation_mm": 2.5,
        "current_soil_moisture": 0.55,
        "data_source": "SIMULATED",
    }

    try:
        initial_obs_count = db.query(Observation).count()
        with patch("backend.app.services.ingestion.scheduler.data_manager.get_village_weather", return_value=mock_weather):
            records_written = scheduler.ingest_once()

        assert records_written > 0, "Expected observations to be written to DB"
        new_obs_count = db.query(Observation).count()
        assert new_obs_count == initial_obs_count + records_written

        # Verify recent observation content
        latest_obs = db.query(Observation).order_by(Observation.id.desc()).first()
        assert latest_obs is not None
        assert latest_obs.variable in ["rainfall_rate_mm_hr", "soil_saturation_ratio"]
        assert latest_obs.value >= 0.0

    finally:
        db.close()
