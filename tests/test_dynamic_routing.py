"""Tests for Dimension 3: Dynamic Evacuation Routing & Real-Time Shelter Balancing."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.routing.dynamic_graph import DynamicEvacuationRouter


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestDynamicRoutingEngine:
    def test_shelter_capacity_rebalancing(self):
        router = DynamicEvacuationRouter()
        # In default state:
        # SHELTER_HARSIL_ARMY has capacity 300, occupancy 275 (91.6% > 90% threshold!)
        # The router MUST divert evacuees from Harsil to SHELTER_SUKHI_COMMUNITY along pedestrian mountain trail
        route = router.find_optimal_evacuation(origin_village_id="VIL_UTK_01", preferred_modality="PEDESTRIAN")
        assert route["path_found"] is True
        assert route["shelter_rebalanced"] is True

        assert "90%" in route["rebalancing_reason"]
        # Destination should NOT be the saturated Harsil army shelter
        assert route["destination_shelter_id"] == "SHELTER_SUKHI_COMMUNITY"
        assert len(route["waypoints"]) >= 2

    def test_normal_routing_when_capacity_available(self):
        router = DynamicEvacuationRouter()
        # Lower occupancy of Harsil shelter below 90%
        router.nodes["SHELTER_HARSIL_ARMY"]["occupancy"] = 150  # 50%
        route = router.find_optimal_evacuation(origin_village_id="VIL_UTK_01")
        assert route["path_found"] is True
        assert route["shelter_rebalanced"] is False
        assert route["destination_shelter_id"] == "SHELTER_HARSIL_ARMY"

    def test_dynamic_road_cutoff_and_trail_fallback(self):
        router = DynamicEvacuationRouter()
        router.nodes["SHELTER_HARSIL_ARMY"]["occupancy"] = 150  # 50%

        # Block the 4x4 road to shelter due to a landslide
        router.set_edge_status("EDGE_HARSIL_TO_ARMY_ROAD", is_blocked=True, block_reason="Landslide Debris")

        # Routing should automatically fall back to the mountain pedestrian trail
        route = router.find_optimal_evacuation(origin_village_id="VIL_UTK_01")
        assert route["path_found"] is True
        assert route["destination_shelter_id"] == "SHELTER_HARSIL_ARMY"
        assert any("EDGE_HARSIL_TO_ARMY_ROAD" in b for b in route["bottlenecks_avoided"])


class TestRoutingEndpoints:
    def test_calculate_route_endpoint(self, client):
        payload = {
            "origin_village_id": "VIL_UTK_01",
            "evacuee_count": 50,
            "preferred_modality": "MULTIMODAL"
        }
        resp = client.post("/api/v1/routing/calculate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["path_found"] is True
        assert "destination_shelter_id" in data
        assert len(data["waypoints"]) > 0

    def test_list_shelters_endpoint(self, client):
        resp = client.get("/api/v1/routing/shelters")
        assert resp.status_code == 200
        shelters = resp.json()
        assert len(shelters) >= 2
        assert any(s["occupancy_pct"] > 90.0 for s in shelters)

    def test_edge_block_endpoint(self, client):
        payload = {
            "edge_id": "EDGE_HARSIL_DHARALI_NH",
            "is_blocked": True,
            "block_reason": "Bhagirathi River Spillage"
        }
        resp = client.post("/api/v1/routing/edge/block", json=payload)
        assert resp.status_code == 200
        assert resp.json()["is_blocked"] is True
