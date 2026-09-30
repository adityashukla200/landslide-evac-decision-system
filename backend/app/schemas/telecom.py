"""Pydantic schemas for Dimension 4: Crisis Telecom, C-DOT Cell Broadcast, NavIC & BLE Beaconing."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CellBroadcastRequest(BaseModel):
    incident_id: str
    severity: str = Field(..., description="Extreme, Severe, Moderate")
    headline_en: str
    headline_hi: str
    polygon_coordinates: List[List[float]] = Field(
        ..., description="List of [lat, lon] polygon points defining the broadcast geofence"
    )
    expiration_minutes: int = 60


class CellBroadcastResponse(BaseModel):
    broadcast_id: str
    status: str = "TRANSMITTED_TO_CBC"
    ts_23_041_serial: str
    message_identifier: int
    language_codes: List[str] = ["en", "hi"]
    target_bts_cells_estimated: int
    dispatched_at: datetime


class NavICBroadcastRequest(BaseModel):
    alert_code: int = Field(..., description="ISRO Emergency Alert Code (1-255)")
    village_id: str
    message_en: str
    message_hi: str


class NavICBroadcastResponse(BaseModel):
    transmission_id: str
    satellite_channel: str = "ISRO-NavIC-L5"
    packet_length_bytes: int
    encoded_hex_packet: str
    crc24_verified: bool
    status: str = "TRANSMITTED_TO_GROUND_STATION"
    timestamp: datetime


class SatelliteBackhaulStatus(BaseModel):
    primary_uplink_active: bool
    primary_uplink_type: str = "FIBER_4G_CELLULAR"
    satellite_fallback_active: bool
    satellite_provider: str = "BSNL_SATELLITE_IOT_IRIDIUM"
    signal_csq: int = Field(..., ge=0, le=31)
    pending_sbd_messages: int
    last_uplink_timestamp: Optional[datetime] = None


class VictimBLEBeacon(BaseModel):
    beacon_uuid: str
    victim_name: Optional[str] = "Anonymous Citizen"
    latitude: float
    longitude: float
    accuracy_m: float = 5.0
    trapped_count: int = 1
    medical_urgent: bool = False
    battery_pct: int = 75
    detected_by_node_id: Optional[str] = None
    rssi_dbm: float = -65.0


class VictimBLEBeaconRecord(VictimBLEBeacon):
    id: str
    first_heard_at: datetime
    last_heard_at: datetime
    rescue_status: str = "PENDING_LOCATE"
