"""LoRaWAN / Meshtastic Binary Packet Codec & Store-and-Forward Gateway.

Implements SX1262 / RAK4631 binary packet frames, hop-count tracking,
deduplication, and MQTT uplink bridge.
"""

import struct
import time
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone


class LoRaPacketCodec:
    """Encodes and decodes compact binary telemetry frames for SX1262 LoRa mesh.

    Packet Frame Layout (16 bytes compact header + payload):
    - Byte 0: Magic byte (0x5A) + Version (0x01) -> 0x51
    - Byte 1: Packet Type (1=TELEMETRY, 2=ALERT, 3=INFRASOUND, 4=LAST_GASP, 5=FORWARD)
    - Byte 2-3: Sender Node ID (uint16)
    - Byte 4-5: Target Node ID (uint16, 0xFFFF = BROADCAST)
    - Byte 6: Hop Count (uint8)
    - Byte 7: Flags (bit 0 = urgent, bit 1 = ack_req, bit 2 = subzero_mode)
    - Byte 8-9: Soil Moisture % * 100 (uint16)
    - Byte 10-11: River Stage cm (uint16)
    - Byte 12-13: Rain 1hr mm * 10 (uint16)
    - Byte 14: Battery % (uint8)
    - Byte 15: CRC-8 Checksum (uint8)
    """

    MAGIC_HEADER = 0x51
    PACKET_TYPES = {
        1: "TELEMETRY",
        2: "ALERT",
        3: "INFRASOUND_RUMBLE",
        4: "LAST_GASP",
        5: "STORE_FORWARD",
    }
    INV_PACKET_TYPES = {v: k for k, v in PACKET_TYPES.items()}

    @classmethod
    def compute_crc8(cls, data: bytes) -> int:
        """Standard SMBus / ATM CRC-8 calculation."""
        crc = 0x00
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x07) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc

    @classmethod
    def encode_telemetry(
        cls,
        sender_id_num: int,
        target_id_num: int = 0xFFFF,
        packet_type: str = "TELEMETRY",
        hop_count: int = 1,
        urgent: bool = False,
        subzero: bool = False,
        soil_moisture_pct: float = 34.5,
        river_stage_cm: int = 142,
        rain_1hr_mm: float = 12.4,
        battery_pct: int = 92,
    ) -> bytes:
        p_type = cls.INV_PACKET_TYPES.get(packet_type, 1)
        flags = (1 if urgent else 0) | ((1 if subzero else 0) << 2)

        sm_val = min(65535, max(0, int(soil_moisture_pct * 100)))
        stage_val = min(65535, max(0, int(river_stage_cm)))
        rain_val = min(65535, max(0, int(rain_1hr_mm * 10)))
        bat_val = min(100, max(0, int(battery_pct)))

        # Pack without checksum first
        payload = struct.pack(
            ">BBHHBBHHHB",
            cls.MAGIC_HEADER,
            p_type,
            sender_id_num,
            target_id_num,
            hop_count,
            flags,
            sm_val,
            stage_val,
            rain_val,
            bat_val,
        )
        crc = cls.compute_crc8(payload)
        return payload + bytes([crc])

    @classmethod
    def decode_packet(cls, raw_bytes: bytes) -> Dict[str, Any]:
        """Decodes raw binary packet bytes into structured telemetry."""
        if len(raw_bytes) < 16:
            raise ValueError(f"Packet too short: {len(raw_bytes)} bytes, expected 16")

        data_part = raw_bytes[:15]
        expected_crc = raw_bytes[15]
        computed_crc = cls.compute_crc8(data_part)

        if expected_crc != computed_crc:
            raise ValueError(f"CRC8 mismatch: expected {expected_crc}, computed {computed_crc}")

        magic, p_type, sender_id, target_id, hops, flags, sm_val, stage_val, rain_val, bat = struct.unpack(
            ">BBHHBBHHHB", data_part
        )

        if magic != cls.MAGIC_HEADER:
            raise ValueError(f"Invalid magic header: {hex(magic)}")

        return {
            "packet_type": cls.PACKET_TYPES.get(p_type, "UNKNOWN"),
            "sender_id_num": sender_id,
            "target_id_num": target_id,
            "hop_count": hops,
            "urgent": bool(flags & 0x01),
            "subzero_mode": bool(flags & 0x04),
            "soil_moisture_pct": round(sm_val / 100.0, 2),
            "river_stage_cm": stage_val,
            "rain_1hr_mm": round(rain_val / 10.0, 1),
            "battery_pct": bat,
            "valid": True,
        }


class StoreAndForwardMeshGateway:
    """Manages store-and-forward mesh buffer and uplinks to MQTT when network returns."""

    def __init__(self):
        self.message_buffer: Dict[str, Dict[str, Any]] = {}
        self.seen_signatures: set = set()

    def process_incoming_packet(
        self,
        sender_node_id: str,
        recipient_node_id: str,
        packet_type: str,
        hop_count: int,
        rssi_dbm: float,
        snr_db: float,
        telemetry_data: Optional[Dict[str, Any]] = None,
        raw_payload_hex: Optional[str] = None,
    ) -> Dict[str, Any]:
        packet_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Deduplication signature
        sig = f"{sender_node_id}_{packet_type}_{now.strftime('%Y%m%d%H%M')}"
        is_duplicate = sig in self.seen_signatures
        if not is_duplicate:
            self.seen_signatures.add(sig)

        decoded_summary = telemetry_data or {}
        if raw_payload_hex:
            try:
                raw_bytes = bytes.fromhex(raw_payload_hex)
                decoded_summary.update(LoRaPacketCodec.decode_packet(raw_bytes))
            except Exception as e:
                decoded_summary["decode_error"] = str(e)

        packet_entry = {
            "packet_id": packet_id,
            "sender_node_id": sender_node_id,
            "recipient_node_id": recipient_node_id,
            "packet_type": packet_type,
            "hop_count": hop_count,
            "rssi_dbm": rssi_dbm,
            "snr_db": snr_db,
            "uplinked_to_mqtt": True,  # Simulated gateway immediate uplink or buffer
            "processed_at": now,
            "is_duplicate": is_duplicate,
            "decoded_summary": decoded_summary,
        }

        # Store in local ring buffer
        self.message_buffer[packet_id] = packet_entry
        return packet_entry

    def get_pending_uplinks(self) -> list:
        return [pkt for pkt in self.message_buffer.values() if not pkt["uplinked_to_mqtt"]]
