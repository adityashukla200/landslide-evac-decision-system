"""Tests for Dimension 4: Crisis Telecom, C-DOT Cell Broadcast, NavIC & BLE Beaconing."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.telecom.broadcast import (
    CDOTCellBroadcastEngine,
    NavICSatelliteMessenger,
    SatelliteBackhaulFailover,
    BLEVictimTracker,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestTelecomServices:
    def test_cdot_cell_broadcast_formatting(self):
        polygon = [
            [31.030, 78.730],
            [31.040, 78.730],
            [31.040, 78.745],
            [31.030, 78.745],
        ]
        res = CDOTCellBroadcastEngine.dispatch_geofenced_broadcast(
            incident_id="INC-HARSIL-2026-09",
            severity="Extreme",
            headline_en="FLASH FLOOD EMERGENCY: Evacuate towards High Ridge immediately.",
            headline_hi="आकस्मिक बाढ़ चेतावनी: तुरंत ऊंचे स्थानों पर जाएं।",
            polygon_coords=polygon,
        )
        assert res["broadcast_id"].startswith("CBC-IND-")
        assert res["status"] == "TRANSMITTED_TO_CBC"
        assert res["message_identifier"] == 4370
        assert res["target_bts_cells_estimated"] >= 4

    def test_navic_packet_encoding_and_crc24(self):
        res = NavICSatelliteMessenger.encode_navic_alert_packet(
            alert_code=14,
            village_id="VIL_UTK_01",
            message_en="GLOF SURGE INCOMING 20M",
            message_hi="ग्लोफ का पानी आ रहा है",
        )
        assert res["satellite_channel"] == "ISRO-NavIC-L5"
        assert res["packet_length_bytes"] >= 52
        assert len(res["encoded_hex_packet"]) > 0
        assert res["crc24_verified"] is True

    def test_satellite_failover_state(self):
        failover = SatelliteBackhaulFailover()
        initial = failover.get_status()
        assert initial["primary_uplink_active"] is True
        assert initial["satellite_fallback_active"] is False

        # Simulate fiber break
        failover.set_primary_failure(True)
        updated = failover.get_status()
        assert updated["primary_uplink_active"] is False
        assert updated["satellite_fallback_active"] is True
        assert updated["signal_csq"] >= 15

    def test_ble_victim_beacon_aggregation(self):
        tracker = BLEVictimTracker()
        rec1 = tracker.register_beacon({
            "beacon_uuid": "VIC-TEST-UUID-1",
            "victim_name": "Devi Prasad",
            "latitude": 31.038,
            "longitude": 78.740,
            "trapped_count": 3,
            "medical_urgent": True,
            "battery_pct": 55,
        })
        assert rec1["id"] == "VIC-001"
        assert rec1["rescue_status"] == "URGENT_TRIAGE"

        # Update same beacon
        rec2 = tracker.register_beacon({
            "beacon_uuid": "VIC-TEST-UUID-1",
            "victim_name": "Devi Prasad",
            "latitude": 31.038,
            "longitude": 78.740,
            "trapped_count": 3,
            "medical_urgent": True,
            "battery_pct": 52,
        })
        assert rec2["battery_pct"] == 52
        assert len(tracker.list_active_victims()) == 1


class TestTelecomEndpoints:
    def test_cdot_broadcast_endpoint(self, client):
        payload = {
            "incident_id": "INC-01",
            "severity": "Extreme",
            "headline_en": "Critical Landslide Alert",
            "headline_hi": "भूस्खलन चेतावनी",
            "polygon_coordinates": [[31.03, 78.73], [31.04, 78.74]],
            "expiration_minutes": 30
        }
        resp = client.post("/api/v1/telecom/cdot/broadcast", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "TRANSMITTED_TO_CBC"

    def test_navic_transmit_endpoint(self, client):
        payload = {
            "alert_code": 10,
            "village_id": "VIL_UTK_01",
            "message_en": "Flash Flood Evacuate",
            "message_hi": "बाढ़ से बचें"
        }
        resp = client.post("/api/v1/telecom/navic/transmit", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "encoded_hex_packet" in data
        assert data["crc24_verified"] is True

    def test_satellite_backhaul_status_endpoint(self, client):
        resp = client.get("/api/v1/telecom/satellite-backhaul/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "satellite_provider" in data
        assert "signal_csq" in data

    def test_ble_victim_endpoints(self, client):
        beacon_payload = {
            "beacon_uuid": "BLE-VICTIM-UNIT-TEST",
            "victim_name": "Citizen Trapped",
            "latitude": 31.035,
            "longitude": 78.738,
            "accuracy_m": 3.5,
            "trapped_count": 1,
            "medical_urgent": True,
            "battery_pct": 82,
            "rssi_dbm": -58.0
        }
        resp = client.post("/api/v1/telecom/ble-victims/beacon", json=beacon_payload)
        assert resp.status_code == 200
        rec = resp.json()
        assert rec["beacon_uuid"] == "BLE-VICTIM-UNIT-TEST"

        resp_list = client.get("/api/v1/telecom/ble-victims/active")
        assert resp_list.status_code == 200
        assert len(resp_list.json()) >= 1
