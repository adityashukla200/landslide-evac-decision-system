"""Tests for Dimension 1: Computer Vision Pipeline & Catchment GNN/PINN Runoff."""

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ai_cv.pipeline import (
    FloodwaterSegmenter,
    StaffGaugeReader,
    DebrisVelocityEstimator,
    FalseAlarmClassifier,
    CVOrchestrator,
)
from backend.app.services.ai_cv.gnn_runoff import CatchmentGNNModel, PINNResidualCorrector, CATCHMENT_STREAM_NETWORK
from backend.app.db.session import SessionLocal
from backend.app.db.models import CitizenReport, Village


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def make_synthetic_flood_image(size=(100, 100)) -> bytes:
    """Create a synthetic muddy/water image with brownish-blue hues."""
    img = Image.new("RGB", size, color=(140, 100, 70))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()



def make_synthetic_dry_image(size=(100, 100)) -> bytes:
    """Create a dry road/vegetation image with bright greens/yellows."""
    img = Image.new("RGB", size, color=(160, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


class TestCVPipelineComponents:
    def test_floodwater_segmenter(self):
        segmenter = FloodwaterSegmenter()
        flood_bytes = make_synthetic_flood_image()
        result = segmenter.segment(flood_bytes)
        assert "water_fraction" in result
        assert 0.0 <= result["water_fraction"] <= 1.0
        assert "confidence" in result
        assert result["water_fraction"] > 0.05

    def test_staff_gauge_reader(self):
        reader = StaffGaugeReader()
        flood_bytes = make_synthetic_flood_image()
        result = reader.estimate_depth(flood_bytes)
        assert "depth_m" in result
        assert 0.0 <= result["depth_m"] <= 10.0
        assert "confidence" in result

    def test_debris_velocity_estimator(self):
        estimator = DebrisVelocityEstimator()
        flood_bytes = make_synthetic_flood_image()
        result = estimator.estimate_velocity(flood_bytes, is_video=False)
        assert "debris_velocity_ms" in result
        assert result["debris_velocity_ms"] >= 0.0
        assert "flow_regime" in result

    def test_false_alarm_classifier(self):
        classifier = FalseAlarmClassifier()
        flood_bytes = make_synthetic_flood_image()
        res_flood = classifier.classify(flood_bytes, reported_flood=True)
        assert res_flood["is_false_alarm"] is False
        assert res_flood["confidence"] > 0.5

        dry_bytes = make_synthetic_dry_image()
        res_dry = classifier.classify(dry_bytes, reported_flood=False)
        assert "is_false_alarm" in res_dry

    def test_cv_orchestrator(self):
        orchestrator = CVOrchestrator()
        flood_bytes = make_synthetic_flood_image()
        analysis = orchestrator.analyze(flood_bytes, media_type="photo", reported_flood=True)
        assert 0.0 <= analysis.water_fraction <= 1.0
        assert analysis.estimated_depth_m >= 0.0
        assert analysis.debris_velocity_ms >= 0.0
        assert isinstance(analysis.is_false_alarm, bool)
        assert analysis.confidence > 0.0
        assert analysis.model_version.startswith("cv-himalaya")


class TestCatchmentGNNPINN:
    def test_gnn_topology_initialization(self):
        gnn = CatchmentGNNModel()
        assert len(CATCHMENT_STREAM_NETWORK) >= 10
        assert CATCHMENT_STREAM_NETWORK[0][0] == "VIL_UTK_01"

    def test_runoff_propagation_and_residual_pinn(self):
        sample_villages = [
            {"id": "VIL_UTK_01", "name": "Harsil", "base_factor_of_safety": 1.35, "rainfall_rate_mm_h": 45.0, "slope_deg": 35.0, "soil_moisture": 0.72},
            {"id": "VIL_UTK_02", "name": "Dharali", "base_factor_of_safety": 1.15, "rainfall_rate_mm_h": 50.0, "slope_deg": 38.0, "soil_moisture": 0.78},
            {"id": "VIL_UTK_03", "name": "Jhala", "base_factor_of_safety": 1.08, "rainfall_rate_mm_h": 65.0, "slope_deg": 42.0, "soil_moisture": 0.85},
        ]
        res = PINNResidualCorrector.apply_catchment_pinn(sample_villages)
        assert len(res) == 3
        harsil = res[0]
        assert "hydrodynamic_discharge_m3_s" in harsil
        assert harsil["hydrodynamic_discharge_m3_s"] > 0.0
        assert "pinn_factor_of_safety" in harsil
        assert harsil["pinn_factor_of_safety"] <= harsil["base_factor_of_safety"]



class TestCVAndGNNEndpoints:
    def test_cv_analyze_direct(self, client):
        img_bytes = make_synthetic_flood_image()
        files = {"file": ("test_flood.jpg", img_bytes, "image/jpeg")}
        data = {"reported_flood": "true"}
        resp = client.post("/api/v1/cv/analyze", files=files, data=data)
        assert resp.status_code == 200
        json_data = resp.json()
        assert "water_fraction" in json_data
        assert "estimated_depth_m" in json_data
        assert "debris_velocity_ms" in json_data
        assert "is_false_alarm" in json_data

    def test_catchment_gnn_endpoint(self, client):
        payload = {
            "hourly_rainfall_mm": {
                "VIL_UTK_01": 70.0,
                "VIL_UTK_02": 80.0
            },
            "antecedent_days": 2
        }
        resp = client.post("/api/v1/cv/catchment-gnn/simulate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert "summary" in data
        assert data["summary"]["total_nodes_simulated"] >= 10
