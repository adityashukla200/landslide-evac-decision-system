"""Tests for Dimension 1: Satellite & Nowcast Integration (Sentinel-1, Sentinel-2, GPM, INSAT-3D)."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.satellite.providers import (
    Sentinel1SARProvider,
    Sentinel2OpticalProvider,
    NASAGPMNowcastProvider,
    INSAT3DCloudburstProvider,
    SatelliteRiskFusionEngine,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestSatelliteProviders:
    def test_sentinel1_sar_provider(self):
        s1 = Sentinel1SARProvider()
        obs = s1.fetch_observation("VIL_UTK_01", lat=31.035, lon=78.738)
        assert obs.sensor == "SENTINEL-1-SAR"
        assert obs.coherence_loss is not None
        assert 0.0 <= obs.coherence_loss <= 1.0
        assert obs.deformation_rate_mm_year is not None

    def test_sentinel2_optical_provider(self):
        s2 = Sentinel2OpticalProvider()
        obs = s2.fetch_observation("VIL_UTK_01", lat=31.035, lon=78.738)
        assert obs.sensor == "SENTINEL-2-MSI"
        assert obs.ndwi is not None
        assert -1.0 <= obs.ndwi <= 1.0
        assert obs.mndwi is not None
        assert -1.0 <= obs.mndwi <= 1.0
        assert obs.cloud_cover_pct >= 0.0

    def test_nasa_gpm_nowcast(self):
        gpm = NASAGPMNowcastProvider()
        obs = gpm.fetch_observation("VIL_UTK_01", lat=31.035, lon=78.738)
        assert obs.sensor == "NASA-GPM-IMERG"
        assert obs.rainfall_rate_mm_hr is not None
        assert obs.rainfall_rate_mm_hr >= 0.0

    def test_insat3d_cloudburst_detection(self):
        insat = INSAT3DCloudburstProvider()
        # Normal cooling rate
        obs_normal = insat.fetch_observation("VIL_UTK_01", lat=31.035, lon=78.738, simulated_cooling_k=-5.0)
        assert obs_normal.sensor == "INSAT-3D-RAPID"
        assert obs_normal.cloudburst_risk is False

        # Severe rapid cooling: -18 K / 15 min (exceeds -15 K threshold)
        obs_severe = insat.fetch_observation("VIL_UTK_01", lat=31.035, lon=78.738, simulated_cooling_k=-18.5)
        assert obs_severe.cloudburst_risk is True
        assert obs_severe.cloud_top_cooling_rate_k_15min < -15.0

    def test_risk_fusion_engine(self):
        fusion = SatelliteRiskFusionEngine()
        res = fusion.fuse_village_satellite_risk(
            village_id="VIL_UTK_01",
            lat=31.035,
            lon=78.738,
            current_risk=0.45
        )
        assert "fused_risk_score" in res
        assert 0.0 <= res["fused_risk_score"] <= 1.0
        assert "delta_risk" in res
        assert "threat_level" in res
        assert "contributing_sensors" in res
        assert len(res["contributing_sensors"]) >= 3


class TestSatelliteEndpoints:
    def test_nowcast_endpoint(self, client):
        resp = client.get("/api/v1/satellite/nowcast", params={"village_id": "VIL_UTK_01"})
        assert resp.status_code == 200
        data = resp.json()
        assert "village_id" in data
        assert data["village_id"] == "VIL_UTK_01"
        assert "fused_risk_score" in data
        assert "observations" in data
        assert len(data["observations"]) >= 1

    def test_observations_history(self, client):
        resp = client.get("/api/v1/satellite/observations", params={"limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
