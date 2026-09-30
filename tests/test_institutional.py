"""Tests for Dimension 5: Institutional Integration (CWC, IMD, NDMA PDNA & CDRI)."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.institutional.cwc_imd import CWCStageConnector, IMDDopplerRadarConnector
from backend.app.services.institutional.pdna_generator import NDMAPDNAGenerator
from backend.app.services.institutional.resilience_index import CommunityResilienceIndexCalculator


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestInstitutionalServices:
    def test_cwc_stage_connector(self):
        stations = CWCStageConnector.get_all_stations()
        assert len(stations) >= 3
        harsil = next(s for s in stations if s["station_code"] == "CWC_HARSIL")
        assert harsil["river"] == "Bhagirathi"
        assert harsil["current_stage_m"] >= harsil["danger_level_m"]
        assert harsil["status"] == "DANGER"

    def test_imd_doppler_radar_connector(self):
        scan = IMDDopplerRadarConnector.fetch_latest_scan()
        assert scan["radar_station"] == "DWR_SURKANDA_DEVI"
        assert scan["reflectivity_dbz"] > 40.0
        assert scan["rain_rate_mm_hr"] > 0.0
        assert scan["convective_cell_detected"] is True

    def test_ndma_pdna_generator(self):
        dossier = NDMAPDNAGenerator.generate_dossier(
            incident_name="Uttarkashi Cloudburst & Flash Flood 2026",
            disaster_type="Flash Flood",
            village_ids=["VIL_UTK_01", "VIL_UTK_02", "VIL_UTK_03"],
            assessor_name="NDMA Field Assessor",
        )
        assert dossier["ndma_standard_compliant"] is True
        assert dossier["villages_assessed_count"] == 3
        assert dossier["total_reconstruction_cost_inr_crores"] > 0.0
        assert len(dossier["sector_breakdown"]) == 5
        assert len(dossier["priority_early_recovery_actions"]) >= 3

    def test_cdri_resilience_calculator(self):
        scores = CommunityResilienceIndexCalculator.calculate_all()
        assert len(scores) >= 5
        harsil_cdri = CommunityResilienceIndexCalculator.calculate_cdri("VIL_UTK_01")
        assert 0.0 <= harsil_cdri["overall_cdri_score"] <= 100.0
        assert harsil_cdri["resilience_tier"] in [
            "TIER_1_ROBUST",
            "TIER_2_MODERATE",
            "TIER_3_VULNERABLE",
            "TIER_4_CRITICAL",
        ]


class TestInstitutionalEndpoints:
    def test_cwc_stages_endpoint(self, client):
        resp = client.get("/api/v1/institutional/cwc/stages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    def test_imd_radar_endpoint(self, client):
        resp = client.get("/api/v1/institutional/imd/radar")
        assert resp.status_code == 200
        data = resp.json()
        assert "reflectivity_dbz" in data

    def test_pdna_generate_endpoint(self, client):
        payload = {
            "incident_name": "Bhagirathi Valley Monsoonal Surge",
            "disaster_type": "Flash Flood",
            "village_ids": ["VIL_UTK_01", "VIL_UTK_02"],
            "assessor_name": "Officer In-Charge"
        }
        resp = client.post("/api/v1/institutional/pdna/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dossier_id"].startswith("PDNA-NDMA-")
        assert data["total_reconstruction_cost_inr_crores"] > 0.0

    def test_cdri_scores_endpoints(self, client):
        resp = client.get("/api/v1/institutional/cdri/scores")
        assert resp.status_code == 200
        assert len(resp.json()) >= 5

        resp_vid = client.get("/api/v1/institutional/cdri/village/VIL_UTK_01")
        assert resp_vid.status_code == 200
        assert resp_vid.json()["village_id"] == "VIL_UTK_01"
