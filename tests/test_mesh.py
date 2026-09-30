"""Tests for Dimension 2: IoT Multi-Hop Edge Mesh (LoRa/Meshtastic), Infrasound GLOF & Solar MPPT."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.mesh.lora_packet import LoRaPacketCodec, StoreAndForwardMeshGateway
from backend.app.services.mesh.infrasound_glof import InfrasoundGLOFDetector
from backend.app.services.mesh.solar_power import SolarPowerManager


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestLoRaCodecAndMeshGateway:
    def test_lora_packet_encode_decode(self):
        encoded = LoRaPacketCodec.encode_telemetry(
            sender_id_num=101,
            target_id_num=0xFFFF,
            packet_type="TELEMETRY",
            hop_count=2,
            urgent=False,
            subzero=True,
            soil_moisture_pct=42.5,
            river_stage_cm=185,
            rain_1hr_mm=25.4,
            battery_pct=88,
        )
        assert len(encoded) == 16
        decoded = LoRaPacketCodec.decode_packet(encoded)
        assert decoded["valid"] is True
        assert decoded["sender_id_num"] == 101
        assert decoded["hop_count"] == 2
        assert decoded["subzero_mode"] is True
        assert decoded["soil_moisture_pct"] == 42.5
        assert decoded["river_stage_cm"] == 185
        assert decoded["rain_1hr_mm"] == 25.4
        assert decoded["battery_pct"] == 88

    def test_lora_crc8_tamper_detection(self):
        encoded = bytearray(LoRaPacketCodec.encode_telemetry(sender_id_num=102))
        # Corrupt one data byte
        encoded[8] ^= 0xFF
        with pytest.raises(ValueError, match="CRC8 mismatch"):
            LoRaPacketCodec.decode_packet(bytes(encoded))

    def test_store_and_forward_gateway_dedup(self):
        gateway = StoreAndForwardMeshGateway()
        res1 = gateway.process_incoming_packet(
            sender_node_id="NODE-HARSIL-01",
            recipient_node_id="BROADCAST",
            packet_type="TELEMETRY",
            hop_count=1,
            rssi_dbm=-75.0,
            snr_db=9.0,
            telemetry_data={"river_stage_cm": 150},
        )
        assert res1["is_duplicate"] is False
        assert res1["uplinked_to_mqtt"] is True

        # Second immediate duplicate packet
        res2 = gateway.process_incoming_packet(
            sender_node_id="NODE-HARSIL-01",
            recipient_node_id="BROADCAST",
            packet_type="TELEMETRY",
            hop_count=1,
            rssi_dbm=-76.0,
            snr_db=8.8,
            telemetry_data={"river_stage_cm": 150},
        )
        assert res2["is_duplicate"] is True


class TestInfrasoundGLOFDetector:
    def test_infrasound_normal_background(self):
        detector = InfrasoundGLOFDetector()
        freqs = [1.0, 5.0, 10.0, 15.0, 20.0, 25.0]
        # Equal diffuse noise across spectrum, low amplitude
        amps = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        res = detector.analyze_spectrum(
            station_id="GEO-GANGOTRI-01",
            village_id="VIL_UTK_05",
            frequencies_hz=freqs,
            spectral_amplitudes_db=amps,
            peak_amplitude_pa=0.4,
        )
        assert res["glof_rumble_detected"] is False
        assert res["action_taken"] == "NORMAL_MONITORING"
        assert res["estimated_lead_time_minutes"] == 0

    def test_infrasound_glof_surge_detection(self):
        detector = InfrasoundGLOFDetector()
        freqs = [1.0, 3.5, 6.0, 9.0, 18.0, 28.0]
        # Massive acoustic energy concentrated in 3.5 - 9.0 Hz band with 4.5 Pa surge
        amps = [5.0, 45.0, 48.0, 42.0, 12.0, 8.0]
        # Run 3 consecutive windows to satisfy rolling window threshold
        res = None
        for _ in range(3):
            res = detector.analyze_spectrum(
                station_id="GEO-GANGOTRI-01",
                village_id="VIL_UTK_05",
                frequencies_hz=freqs,
                spectral_amplitudes_db=amps,
                peak_amplitude_pa=4.2,
            )
        assert res["glof_rumble_detected"] is True
        assert res["estimated_lead_time_minutes"] == 25
        assert "TRIGGER_EDGE_SIREN" in res["action_taken"]
        assert res["confidence"] > 0.70


class TestSolarMPPTEngine:
    def test_subzero_lithium_protection(self):
        res = SolarPowerManager.evaluate_node_power(
            node_id="NODE-HARSIL-01",
            solar_panel_v=5.8,
            battery_v=3.32,
            charge_current_ma=450.0,
            battery_temp_c=-8.5,  # Sub-zero Himalayan winter
        )
        assert res["subzero_protection_active"] is True
        assert res["charge_throttled"] is True
        assert "SUBZERO_CUTOFF" in res["mppt_state"]

    def test_critical_battery_last_gasp(self):
        res = SolarPowerManager.evaluate_node_power(
            node_id="NODE-HARSIL-01",
            solar_panel_v=0.5,
            battery_v=2.95,
            charge_current_ma=0.0,
            battery_temp_c=5.0,
        )
        assert res["battery_pct"] < 15.0
        assert res["last_gasp_warning_triggered"] is True
        assert res["recommended_sleep_interval_sec"] == 900
        assert "CRITICAL_LOW_POWER" in res["mppt_state"]


class TestMeshEndpoints:
    def test_mesh_packet_ingest_endpoint(self, client):
        raw_hex = LoRaPacketCodec.encode_telemetry(
            sender_id_num=201,
            target_id_num=0xFFFF,
            packet_type="TELEMETRY",
            soil_moisture_pct=38.0,
            river_stage_cm=160,
        ).hex()
        payload = {
            "sender_node_id": "MESH-HARSIL-01",
            "recipient_node_id": "BROADCAST",
            "packet_type": "TELEMETRY",
            "hop_count": 1,
            "rssi_dbm": -82.0,
            "snr_db": 9.5,
            "raw_payload_hex": raw_hex,
        }
        resp = client.post("/api/v1/mesh/packets/ingest", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["sender_node_id"] == "MESH-HARSIL-01"
        assert data["uplinked_to_mqtt"] is True
        assert data["decoded_summary"]["river_stage_cm"] == 160

    def test_mesh_nodes_endpoint(self, client):
        resp = client.get("/api/v1/mesh/nodes")
        assert resp.status_code == 200
        nodes = resp.json()
        assert len(nodes) >= 1
        assert "node_id" in nodes[0]
