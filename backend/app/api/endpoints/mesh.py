"""API Endpoints for Dimension 2: IoT LoRa/Meshtastic Edge Mesh, Infrasound & Solar Power."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import MeshNode, MeshPacket
from backend.app.schemas.mesh import (
    MeshNodeCreate,
    MeshNodeResponse,
    MeshPacketIngest,
    MeshPacketResponse,
    InfrasoundSampleInput,
    InfrasoundDetectionResult,
    SolarPowerTelemetryInput,
    SolarPowerHealthReport,
)
from backend.app.services.mesh.lora_packet import StoreAndForwardMeshGateway, LoRaPacketCodec
from backend.app.services.mesh.infrasound_glof import InfrasoundGLOFDetector
from backend.app.services.mesh.solar_power import SolarPowerManager

router = APIRouter(prefix="/mesh", tags=["IoT Multi-Hop Mesh"])
mesh_gateway = StoreAndForwardMeshGateway()
infrasound_detector = InfrasoundGLOFDetector()



@router.post("/packets/ingest", response_model=MeshPacketResponse)
def ingest_mesh_packet(payload: MeshPacketIngest, db: Session = Depends(get_db)):
    """Ingest a multi-hop LoRa / Meshtastic packet from field gateway."""
    processed = mesh_gateway.process_incoming_packet(
        sender_node_id=payload.sender_node_id,
        recipient_node_id=payload.recipient_node_id,
        packet_type=payload.packet_type,
        hop_count=payload.hop_count,
        rssi_dbm=payload.rssi_dbm,
        snr_db=payload.snr_db,
        telemetry_data=payload.telemetry_data,
        raw_payload_hex=payload.raw_payload_hex,
    )

    # Ensure node exists
    node = db.query(MeshNode).filter(MeshNode.id == payload.sender_node_id).first()
    if not node:
        node = MeshNode(
            id=payload.sender_node_id,
            node_hex=f"!{payload.sender_node_id[:8].lower()}",
            hardware_model="RAK4631_SX1262",
            role="ROUTER_CLIENT",
            battery_pct=90.0,
            rssi_dbm=int(payload.rssi_dbm),
            snr_db=payload.snr_db,
        )
        db.add(node)
        db.commit()

    db_packet = MeshPacket(
        id=processed["packet_id"],
        node_id=payload.sender_node_id,
        packet_type=payload.packet_type,
        payload_hex=payload.raw_payload_hex or "00",
        decoded_json=processed["decoded_summary"],
        hop_count=payload.hop_count,
        gateway_uplinked=True,
    )
    db.add(db_packet)

    # Update node last heard
    node.last_heard_at = processed["processed_at"]
    if "battery_pct" in processed["decoded_summary"]:
        node.battery_pct = float(processed["decoded_summary"]["battery_pct"])

    db.commit()

    return MeshPacketResponse(
        packet_id=processed["packet_id"],
        sender_node_id=payload.sender_node_id,
        recipient_node_id=payload.recipient_node_id,
        packet_type=payload.packet_type,
        hop_count=payload.hop_count,
        uplinked_to_mqtt=True,
        processed_at=processed["processed_at"],
        decoded_summary=processed["decoded_summary"],
    )


@router.get("/nodes", response_model=List[MeshNodeResponse])
def list_mesh_nodes(village_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List deployed LoRa/Meshtastic mesh nodes."""
    query = db.query(MeshNode)
    if village_id:
        query = query.filter(MeshNode.village_id == village_id)
    nodes = query.all()
    if not nodes:
        default_nodes = [
            MeshNode(
                id="MESH-HARSIL-01",
                node_hex="!a4b801",
                hardware_model="RAK4631_SX1262",
                village_id="VIL_UTK_01",
                battery_pct=94.0,
            ),
            MeshNode(
                id="MESH-DHARALI-02",
                node_hex="!a4b802",
                hardware_model="ESP32_SX1262",
                village_id="VIL_UTK_02",
                battery_pct=88.5,
            ),
            MeshNode(
                id="MESH-GANGOTRI-03",
                node_hex="!a4b803",
                hardware_model="RAK4631_SX1262",
                village_id="VIL_UTK_05",
                battery_pct=76.0,
            ),
        ]
        for dn in default_nodes:
            db.add(dn)
        db.commit()
        nodes = default_nodes

    return [
        MeshNodeResponse(
            id=n.id,
            node_id=n.id,
            node_hex=n.node_hex,
            hardware_type=n.hardware_model,
            village_id=n.village_id,
            latitude=31.035,
            longitude=78.738,
            battery_pct=n.battery_pct,
            is_online=True,
            hop_count_to_gateway=1,
            last_heard_at=n.last_heard_at,
        )
        for n in nodes
    ]



@router.post("/infrasound/analyze", response_model=InfrasoundDetectionResult)
def analyze_infrasound_stream(payload: InfrasoundSampleInput):
    """Analyze geophone / MEMS infrasound 1-30Hz spectrum for GLOF acoustic signatures."""
    res = infrasound_detector.analyze_spectrum(
        station_id=payload.station_id,
        village_id=payload.village_id,
        frequencies_hz=payload.frequencies_hz,
        spectral_amplitudes_db=payload.spectral_amplitudes_db,
        peak_amplitude_pa=payload.peak_amplitude_pa,
    )
    return InfrasoundDetectionResult(**res)


@router.post("/power/evaluate", response_model=SolarPowerHealthReport)
def evaluate_solar_power(payload: SolarPowerTelemetryInput):
    """Evaluate MPPT state machine, sub-zero protection, and deep-sleep recommendations."""
    res = SolarPowerManager.evaluate_node_power(
        node_id=payload.node_id,
        solar_panel_v=payload.solar_panel_v,
        battery_v=payload.battery_v,
        charge_current_ma=payload.charge_current_ma,
        battery_temp_c=payload.battery_temp_c,
        load_current_ma=payload.load_current_ma,
    )
    return SolarPowerHealthReport(**res)
