"""Pydantic schemas for IoT Multi-Hop LoRaWAN/Meshtastic Edge Mesh, Infrasound & Solar Power."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MeshNodeBase(BaseModel):
    node_id: str = Field(..., description="Unique node ID (e.g. MESH-UTK-01-A)")
    hardware_type: str = Field(default="RAK4631_SX1262", description="Hardware class: ESP32_SX1262, RAK4631, HELTEC_V3")
    village_id: Optional[str] = Field(None, description="Associated village ID")
    latitude: float
    longitude: float
    firmware_version: str = "v2.4.1-mesh-prod"


class MeshNodeCreate(MeshNodeBase):
    pass


class MeshNodeResponse(MeshNodeBase):
    id: str
    battery_pct: float = 100.0

    battery_temp_c: float = 20.0
    solar_panel_v: float = 6.0
    is_online: bool = True
    hop_count_to_gateway: int = 1
    last_heard_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeshPacketIngest(BaseModel):
    sender_node_id: str
    recipient_node_id: str = "BROADCAST"
    packet_type: str = Field(..., description="TELEMETRY, ALERT, INFRASOUND_RUMBLE, LAST_GASP, STORE_FORWARD")
    hop_count: int = 1
    rssi_dbm: float = -85.0
    snr_db: float = 8.5
    raw_payload_hex: Optional[str] = None
    telemetry_data: Optional[Dict[str, Any]] = None


class MeshPacketResponse(BaseModel):
    packet_id: str
    sender_node_id: str
    recipient_node_id: str
    packet_type: str
    hop_count: int
    uplinked_to_mqtt: bool = True
    processed_at: datetime
    decoded_summary: Dict[str, Any]


class InfrasoundSampleInput(BaseModel):
    station_id: str
    village_id: str
    frequencies_hz: List[float] = Field(..., description="Sampled frequencies 1-30Hz")
    spectral_amplitudes_db: List[float] = Field(..., description="Spectral power in dB")
    peak_amplitude_pa: float = Field(..., description="Peak acoustic pressure in Pascals")
    timestamp: Optional[datetime] = None


class InfrasoundDetectionResult(BaseModel):
    station_id: str
    village_id: str
    dominant_frequency_hz: float
    infrasound_energy_ratio: float
    anomaly_score: float
    glof_rumble_detected: bool
    confidence: float
    estimated_lead_time_minutes: int
    action_taken: str


class SolarPowerTelemetryInput(BaseModel):
    node_id: str
    solar_panel_v: float
    battery_v: float
    charge_current_ma: float
    battery_temp_c: float
    load_current_ma: float = 35.0


class SolarPowerHealthReport(BaseModel):
    node_id: str
    battery_pct: float
    mppt_state: str = Field(..., description="MPPT_OPTIMAL, FLOAT, SUBZERO_THROTTLE, CRITICAL_LOW_POWER")
    subzero_protection_active: bool
    charge_throttled: bool
    recommended_sleep_interval_sec: int
    last_gasp_warning_triggered: bool
    estimated_autonomy_hours: float
