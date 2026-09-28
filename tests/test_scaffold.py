"""Unit tests verifying database scaffold, models, seed data, and health endpoint."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.db.models import (
    Village,
    Sensor,
    Observation,
    RiskAssessment,
    Alert,
    Recipient,
    AlertDelivery,
    Shelter,
    Route,
)
from scripts.seed_data import seed_database


@pytest.fixture(scope="module")
def db_session():
    """Module-level database session fixture."""
    Base.metadata.create_all(bind=engine)
    seed_database()
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


def test_database_tables_exist():
    """Verify that all 9 required tables are registered in the schema."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    required_tables = [
        "villages",
        "sensors",
        "observations",
        "risk_assessments",
        "alerts",
        "alert_deliveries",
        "recipients",
        "shelters",
        "routes",
    ]

    for table in required_tables:
        assert table in table_names, f"Expected table '{table}' not found in database."


def test_seed_villages_count_and_properties(db_session):
    """Verify that exactly 25 synthetic Uttarkashi villages are seeded with correct attributes."""
    villages = db_session.query(Village).all()
    assert len(villages) == 25, f"Expected 25 villages, found {len(villages)}"

    for v in villages:
        assert v.district == "Uttarkashi"
        assert 30.5 <= v.lat <= 31.3, f"Latitude {v.lat} out of realistic Uttarkashi bounds"
        assert 78.0 <= v.lon <= 78.9, f"Longitude {v.lon} out of realistic Uttarkashi bounds"
        assert 800.0 <= v.elevation <= 3200.0, f"Elevation {v.elevation} out of realistic range"
        assert v.population > 0, "Village population must be positive"

        # Verify geometry parsing into Shapely
        geom = v.to_shapely_geom()
        assert geom is not None
        assert geom.is_valid


def test_seed_sensors_and_shelters(db_session):
    """Verify that each village has assigned sensors, shelters, routes, and recipients."""
    villages = db_session.query(Village).all()

    for v in villages:
        # Each village must have at least 2 sensors (rain + soil moisture)
        sensors = db_session.query(Sensor).filter_by(village_id=v.id).all()
        assert len(sensors) >= 2
        sensor_types = {s.type for s in sensors}
        assert "rainfall" in sensor_types
        assert "soil_moisture" in sensor_types

        # Shelter
        shelter = db_session.query(Shelter).filter_by(village_id=v.id).first()
        assert shelter is not None
        assert shelter.capacity >= 250

        # Evacuation Route
        route = db_session.query(Route).filter_by(from_village=v.id).first()
        assert route is not None
        assert route.length_m > 0
        assert route.est_walk_minutes > 0
        assert 0.0 <= route.cut_risk <= 1.0

        # Recipients (Volunteer + Vulnerable)
        recipients = db_session.query(Recipient).filter_by(village_id=v.id).all()
        assert len(recipients) >= 2
        assert any(r.vulnerable_flag for r in recipients)


def test_fastapi_health_endpoint(client):
    """Verify that GET /health returns 200 OK and connected database status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "version" in data
    assert "timestamp" in data


def test_fastapi_root_endpoint(client):
    """Verify that GET / returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
