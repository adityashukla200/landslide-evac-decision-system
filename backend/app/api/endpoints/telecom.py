"""API Endpoints for Dimension 4: Crisis Telecom, C-DOT Cell Broadcast, NavIC & BLE Beaconing."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import EmergencyBroadcastLog
from backend.app.schemas.telecom import (
    CellBroadcastRequest,
    CellBroadcastResponse,
    NavICBroadcastRequest,
    NavICBroadcastResponse,
    SatelliteBackhaulStatus,
    VictimBLEBeacon,
    VictimBLEBeaconRecord,
)
from backend.app.services.telecom.broadcast import (
    CDOTCellBroadcastEngine,
    NavICSatelliteMessenger,
    SatelliteBackhaulFailover,
    BLEVictimTracker,
)

router = APIRouter(prefix="/telecom", tags=["Crisis Telecom & Broadcast"])
satellite_failover = SatelliteBackhaulFailover()
ble_tracker = BLEVictimTracker()


@router.post("/cdot/broadcast", response_model=CellBroadcastResponse)
def trigger_cdot_cell_broadcast(request: CellBroadcastRequest, db: Session = Depends(get_db)):
    """Dispatch geo-fenced C-DOT Cell Broadcast (3GPP TS 23.041) to local mobile towers."""
    res = CDOTCellBroadcastEngine.dispatch_geofenced_broadcast(
        incident_id=request.incident_id,
        severity=request.severity,
        headline_en=request.headline_en,
        headline_hi=request.headline_hi,
        polygon_coords=request.polygon_coordinates,
        expiration_minutes=request.expiration_minutes,
    )

    # Log broadcast to DB
    log = EmergencyBroadcastLog(
        id=res["broadcast_id"],
        channel="C-DOT-CELL-BROADCAST",
        alert_tier=request.severity.upper(),
        target_area_wkt=str(request.polygon_coordinates),
        message_text=request.headline_en[:250],
        protocol_payload={"headline_hi": request.headline_hi, "cells": res["target_bts_cells_estimated"]},
        dispatch_status="SUCCESS",
        delivered_count=res["target_bts_cells_estimated"],
    )
    db.add(log)
    db.commit()

    return CellBroadcastResponse(**res)


@router.post("/navic/transmit", response_model=NavICBroadcastResponse)
def transmit_navic_satellite_alert(request: NavICBroadcastRequest, db: Session = Depends(get_db)):
    """Transmit emergency message via ISRO NavIC (IRNSS) L5-band satellite channel."""
    res = NavICSatelliteMessenger.encode_navic_alert_packet(
        alert_code=request.alert_code,
        village_id=request.village_id,
        message_en=request.message_en,
        message_hi=request.message_hi,
    )

    log = EmergencyBroadcastLog(
        id=res["transmission_id"],
        channel="ISRO-NAVIC-L5",
        alert_tier="EVACUATE",
        message_text=request.message_en[:250],
        protocol_payload={"message_hi": request.message_hi, "packet_hex": res["encoded_hex_packet"]},
        dispatch_status="SUCCESS",
        delivered_count=1,
    )
    db.add(log)
    db.commit()


    return NavICBroadcastResponse(**res)


@router.get("/satellite-backhaul/status", response_model=SatelliteBackhaulStatus)
def get_satellite_backhaul_status():
    """Check health and fallback status of terrestrial 4G/fiber vs BSNL/Iridium satellite IoT."""
    return SatelliteBackhaulStatus(**satellite_failover.get_status())


@router.post("/satellite-backhaul/simulate-failover")
def simulate_telecom_cut(cellular_failed: bool = True):
    """Simulate terrestrial fiber cut and automatic satellite IoT failover activation."""
    satellite_failover.set_primary_failure(cellular_failed)
    return {"status": "UPDATED", "satellite_fallback_active": cellular_failed}


@router.post("/ble-victims/beacon", response_model=VictimBLEBeaconRecord)
def ingest_victim_ble_beacon(beacon: VictimBLEBeacon):
    """Register or update an offline Bluetooth LE beacon emitted from a citizen trapped under rubble."""
    rec = ble_tracker.register_beacon(beacon.dict())
    return VictimBLEBeaconRecord(**rec)


@router.get("/ble-victims/active", response_model=List[VictimBLEBeaconRecord])
def list_active_ble_victims():
    """Retrieve real-time list of detected BLE victim beacons for NDRF search and rescue."""
    victims = ble_tracker.list_active_victims()
    if not victims:
        # Provide sample seed victim beacon
        sample = ble_tracker.register_beacon({
            "beacon_uuid": "BLE-VICTIM-HARSIL-4A",
            "victim_name": "Ramesh Singh (Reported 2 trapped)",
            "latitude": 31.036,
            "longitude": 78.739,
            "accuracy_m": 4.2,
            "trapped_count": 2,
            "medical_urgent": True,
            "battery_pct": 68,
            "rssi_dbm": -62.0,
            "detected_by_node_id": "MESH-HARSIL-01",
        })
        victims = [sample]
    return [VictimBLEBeaconRecord(**v) for v in victims]
