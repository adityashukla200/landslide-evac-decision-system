"""SQLAlchemy database models with dual PostGIS/SQLite geometry support."""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
import shapely.wkt
import shapely.geometry

from backend.app.core.config import settings
from backend.app.db.session import Base

# Determine geometry column type based on active database engine
if settings.is_postgres:
    from geoalchemy2 import Geometry
    GeometryType = Geometry(geometry_type="GEOMETRY", srid=4326)
else:
    # On SQLite: Store geometry as GeoJSON / WKT text
    GeometryType = Text


class Village(Base):
    """Village or administrative ward in a hilly district."""

    __tablename__ = "villages"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    district = Column(String(64), nullable=False, index=True)
    geometry = Column(GeometryType, nullable=True)
    population = Column(Integer, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    elevation = Column(Float, nullable=False)  # in meters

    # Relationships
    sensors = relationship("Sensor", back_populates="village", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="village", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="village", cascade="all, delete-orphan")
    recipients = relationship("Recipient", back_populates="village", cascade="all, delete-orphan")
    shelters = relationship("Shelter", back_populates="village", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="village", cascade="all, delete-orphan")
    thresholds = relationship("VillageThreshold", back_populates="village", uselist=False, cascade="all, delete-orphan")
    citizen_reports = relationship("CitizenReport", back_populates="village", cascade="all, delete-orphan")

    def to_shapely_geom(self) -> Optional[Any]:
        """Convert geometry representation to a Shapely shape object."""
        if not self.geometry:
            return shapely.geometry.Point(self.lon, self.lat)
        if isinstance(self.geometry, str):
            try:
                # Attempt parsing as GeoJSON string first, then WKT
                if self.geometry.strip().startswith("{"):
                    return shapely.geometry.shape(json.loads(self.geometry))
                return shapely.wkt.loads(self.geometry)
            except Exception:
                return shapely.geometry.Point(self.lon, self.lat)
        # Postgres GeoAlchemy2 element
        try:
            from geoalchemy2.shape import to_shape
            return to_shape(self.geometry)
        except Exception:
            return shapely.geometry.Point(self.lon, self.lat)


class Sensor(Base):
    """Ground observation station or gauge."""

    __tablename__ = "sensors"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)
    type = Column(String(32), nullable=False)  # rainfall, soil_moisture, river_gauge
    status = Column(String(32), nullable=False, default="active")  # active, stuck, offline
    last_seen = Column(DateTime, nullable=True)

    # Relationships
    village = relationship("Village", back_populates="sensors")
    observations = relationship("Observation", back_populates="sensor", cascade="all, delete-orphan")


class Observation(Base):
    """Time-series sensor telemetry reading."""

    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False, index=True)
    sensor_id = Column(String(64), ForeignKey("sensors.id"), nullable=False, index=True)
    variable = Column(String(32), nullable=False)  # rainfall_rate_mm_hr, soil_moisture_pct, river_level_m
    value = Column(Float, nullable=False)

    # Relationships
    sensor = relationship("Sensor", back_populates="observations")


class RiskAssessment(Base):
    """Computed hazard risk prediction with conformal bounds."""

    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)
    probability = Column(Float, nullable=False)  # Hazard event probability [0, 1]
    lower = Column(Float, nullable=False)        # Conformal interval lower bound
    upper = Column(Float, nullable=False)        # Conformal interval upper bound
    tier = Column(String(16), nullable=False)    # GREEN, YELLOW, ORANGE, RED
    explanation_json = Column(JSON, nullable=True)  # Factor of Safety, Analog storm match details

    # Relationships
    village = relationship("Village", back_populates="risk_assessments")


class Alert(Base):
    """Actionable evacuation alert directive."""

    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)
    tier = Column(String(16), nullable=False)
    message = Column(String(160), nullable=False)  # Strict max 160-char plain language directive
    drill_flag = Column(Boolean, default=False, nullable=False)
    cap_xml = Column(Text, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    village = relationship("Village", back_populates="alerts")
    deliveries = relationship("AlertDelivery", back_populates="alert", cascade="all, delete-orphan")


class Recipient(Base):
    """Village resident, vulnerable citizen, or community volunteer."""

    __tablename__ = "recipients"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)
    phone = Column(String(32), nullable=False)
    language = Column(String(8), nullable=False, default="en")  # en, hi
    vulnerable_flag = Column(Boolean, nullable=False, default=False)
    volunteer_id = Column(String(64), ForeignKey("recipients.id"), nullable=True)

    # Relationships
    village = relationship("Village", back_populates="recipients")
    deliveries = relationship("AlertDelivery", back_populates="recipient")


class AlertDelivery(Base):
    """Delivery and acknowledgment tracking for each tier in the alert ladder."""

    __tablename__ = "alert_deliveries"

    id = Column(String(64), primary_key=True, index=True)
    alert_id = Column(String(64), ForeignKey("alerts.id"), nullable=False, index=True)
    recipient_id = Column(String(64), ForeignKey("recipients.id"), nullable=False, index=True)
    channel = Column(String(32), nullable=False)  # CELL_BROADCAST, SMS, IVR, VOLUNTEER, SIREN
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, SENT, ACKNOWLEDGED, FAILED
    sent_at = Column(DateTime, nullable=True)
    acked_at = Column(DateTime, nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="deliveries")
    recipient = relationship("Recipient", back_populates="deliveries")


class Shelter(Base):
    """Designated safe high-ground refuge shelter or community hall."""

    __tablename__ = "shelters"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=True)
    geometry = Column(GeometryType, nullable=True)
    capacity = Column(Integer, nullable=False)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)

    # Relationships
    village = relationship("Village", back_populates="shelters")
    routes = relationship("Route", back_populates="shelter", cascade="all, delete-orphan")


class Route(Base):
    """Pre-computed or dynamic evacuation route from village to designated shelter."""

    __tablename__ = "routes"

    id = Column(String(64), primary_key=True, index=True)
    from_village = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)
    to_shelter = Column(String(64), ForeignKey("shelters.id"), nullable=False, index=True)
    length_m = Column(Float, nullable=False)
    est_walk_minutes = Column(Float, nullable=False)
    cut_risk = Column(Float, nullable=False, default=0.0)  # Dynamic hazard severance probability [0, 1]

    # Relationships
    village = relationship("Village", foreign_keys=[from_village], back_populates="routes")
    shelter = relationship("Shelter", foreign_keys=[to_shelter], back_populates="routes")


class VillageThreshold(Base):
    """Per-village Bayes-optimal operational thresholds and cost weighting configuration."""

    __tablename__ = "village_thresholds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, unique=True, index=True)
    cost_miss = Column(Float, nullable=False)
    cost_false_alarm = Column(Float, nullable=False)
    bayes_optimal_threshold = Column(Float, nullable=False)
    watch_threshold = Column(Float, nullable=False)
    warning_threshold = Column(Float, nullable=False)
    evacuate_threshold = Column(Float, nullable=False)
    max_alerts_per_year = Column(Integer, nullable=False, default=15)
    last_modified_by = Column(String(64), nullable=False, default="system")
    last_modified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    change_reason = Column(Text, nullable=True)
    audit_log = Column(JSON, nullable=True, default=list)

    # Relationships
    village = relationship("Village", back_populates="thresholds")


class CommunityReport(Base):
    """Citizen or ward-officer crowd-sourced hazard report vetted as ground-truth."""

    __tablename__ = "community_reports"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    photo_url = Column(String(512), nullable=True)
    text = Column(Text, nullable=False)
    reporter_name = Column(String(128), nullable=True)
    reporter_phone = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING_REVIEW")  # PENDING_REVIEW, VERIFIED, REJECTED
    is_ground_truth_candidate = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Relationships
    village = relationship("Village")


class CitizenReport(Base):
    """Citizen ground-truth hazard report with geotagged media."""

    __tablename__ = "citizen_reports"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    media_type = Column(String(16), nullable=False)  # "photo" or "video"
    file_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), nullable=True)
    caption = Column(Text, nullable=True)
    reported_flood = Column(Boolean, nullable=False, default=True)
    reporter_phone = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, verified, rejected, duplicate
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    audit_log = Column(JSON, nullable=True, default=list)

    # Advanced Computer Vision (CV) Analysis
    cv_water_fraction = Column(Float, nullable=True)  # 0.0 - 1.0 flood extent fraction
    cv_estimated_depth_m = Column(Float, nullable=True)  # estimated flood stage in meters
    cv_debris_velocity_ms = Column(Float, nullable=True)  # debris flow velocity m/s
    cv_is_false_alarm = Column(Boolean, nullable=True, default=False)
    cv_confidence = Column(Float, nullable=True)  # model prediction confidence 0.0 - 1.0
    cv_model_version = Column(String(64), nullable=True)
    cv_features = Column(JSON, nullable=True, default=dict)  # contours, bounding boxes, optical flow
    cv_processed_at = Column(DateTime, nullable=True)

    # Relationships
    village = relationship("Village", back_populates="citizen_reports")


# =============================================================================
# Dimension 1: Satellite & Remote Sensing Models
# =============================================================================

class SatelliteObservation(Base):
    """Satellite remote sensing product (Sentinel-1 SAR, Sentinel-2 Optical, NASA GPM, INSAT-3D)."""

    __tablename__ = "satellite_observations"

    id = Column(String(64), primary_key=True, index=True)
    satellite_source = Column(String(32), nullable=False, index=True)  # SENTINEL_1, SENTINEL_2, NASA_GPM, INSAT_3D
    acquisition_time = Column(DateTime, nullable=False, index=True)
    product_type = Column(String(64), nullable=False, index=True)  # SAR_COHERENCE, OPTICAL_MNDWI, IMERG_NOWCAST, INSAT_TIR_COOLING
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=True, index=True)
    bbox_geojson = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=False, default=dict)  # extracted physical metrics
    risk_score_boost = Column(Float, nullable=False, default=0.0)  # calibrated threat bump [-0.5 to +0.5]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    village = relationship("Village")


# =============================================================================
# Dimension 2: IoT Multi-Hop Mesh Models (LoRa / Meshtastic / Infrasound)
# =============================================================================

class MeshNode(Base):
    """LoRa / Meshtastic multi-hop edge relay node."""

    __tablename__ = "mesh_nodes"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=True, index=True)
    node_hex = Column(String(16), unique=True, nullable=False, index=True)  # !a4b8c9d0
    hardware_model = Column(String(32), nullable=False, default="SX1262_ESP32")
    role = Column(String(32), nullable=False, default="ROUTER_CLIENT")  # ROUTER, GATEWAY, SENSOR, REPEATER
    battery_mv = Column(Integer, nullable=False, default=3700)
    battery_pct = Column(Float, nullable=False, default=100.0)
    snr_db = Column(Float, nullable=False, default=8.5)
    rssi_dbm = Column(Integer, nullable=False, default=-85)
    infrasound_trigger = Column(Boolean, nullable=False, default=False)  # 1-30Hz GLOF rumble flag
    last_heard_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    village = relationship("Village")


class MeshPacket(Base):
    """Raw and decoded LoRaWAN / Meshtastic packet log."""

    __tablename__ = "mesh_packets"

    id = Column(String(64), primary_key=True, index=True)
    node_id = Column(String(64), ForeignKey("mesh_nodes.id"), nullable=False, index=True)
    packet_type = Column(String(32), nullable=False)  # TELEMETRY, ALERT, INFRASOUND_RUMBLE, POSITION
    payload_hex = Column(String(256), nullable=False)
    decoded_json = Column(JSON, nullable=False, default=dict)
    hop_count = Column(Integer, nullable=False, default=0)
    gateway_uplinked = Column(Boolean, nullable=False, default=False)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    node = relationship("MeshNode")


# =============================================================================
# Dimension 3: Dynamic Evacuation & Shelter Capacity Models
# =============================================================================

class RouteSegmentLiveStatus(Base):
    """Real-time passable / blocked status of evacuation trail or roadway segment."""

    __tablename__ = "route_segment_live_status"

    id = Column(String(64), primary_key=True, index=True)
    route_id = Column(String(64), ForeignKey("routes.id"), nullable=False, index=True)
    is_blocked = Column(Boolean, nullable=False, default=False)
    block_reason = Column(String(64), nullable=True)  # RIVER_SURGE, DEBRIS_BLOCKAGE, BRIDGE_DAMAGE, ROCKFALL
    current_water_depth_m = Column(Float, nullable=False, default=0.0)
    landslide_runout_prob = Column(Float, nullable=False, default=0.0)
    dynamic_travel_multiplier = Column(Float, nullable=False, default=1.0)  # 1.0=clear, >5.0=severely delayed, 999=impassable
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    route = relationship("Route")


class ShelterLiveStatus(Base):
    """Dynamic shelter occupancy and real-time load balancing diversion."""

    __tablename__ = "shelter_live_status"

    id = Column(String(64), primary_key=True, index=True)
    shelter_id = Column(String(64), ForeignKey("shelters.id"), unique=True, nullable=False, index=True)
    current_occupants = Column(Integer, nullable=False, default=0)
    capacity = Column(Integer, nullable=False, default=100)
    occupancy_pct = Column(Float, nullable=False, default=0.0)
    is_overflow_diverting = Column(Boolean, nullable=False, default=False)  # True when >90% full
    recommended_divert_shelter_id = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    shelter = relationship("Shelter")


# =============================================================================
# Dimension 4: Extreme-Crisis Telecom & Broadcast Models
# =============================================================================

class EmergencyBroadcastLog(Base):
    """Record of C-DOT Cell Broadcast Engine, NavIC, and Satellite-IoT dispatches."""

    __tablename__ = "emergency_broadcast_logs"

    id = Column(String(64), primary_key=True, index=True)
    channel = Column(String(32), nullable=False, index=True)  # CDOT_CBE, NAVIC_IRNSS, BSNL_SAT_IOT, BLE_BEACON
    alert_tier = Column(String(32), nullable=False)  # EVACUATE, WARNING, WATCH
    target_area_wkt = Column(Text, nullable=True)
    message_text = Column(String(256), nullable=False)
    protocol_payload = Column(JSON, nullable=True, default=dict)
    dispatch_status = Column(String(32), nullable=False, default="SUCCESS")  # SUCCESS, TRANSMITTING, FAILED
    delivered_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# =============================================================================
# Dimension 5: Institutional & Post-Disaster Needs Assessment (PDNA) Models
# =============================================================================

class PDNADossier(Base):
    """Automated Post-Disaster Needs Assessment dossier (NDMA format)."""

    __tablename__ = "pdna_dossiers"

    id = Column(String(64), primary_key=True, index=True)
    district = Column(String(64), nullable=False, index=True)
    event_title = Column(String(128), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    impacted_villages_count = Column(Integer, nullable=False, default=0)
    total_population_affected = Column(Integer, nullable=False, default=0)
    displaced_population = Column(Integer, nullable=False, default=0)
    infrastructure_damage_score = Column(Float, nullable=False, default=0.0)  # 0 to 10
    estimated_economic_loss_cr = Column(Float, nullable=False, default=0.0)  # In Crores INR
    verified_citizen_reports_count = Column(Integer, nullable=False, default=0)
    executive_summary = Column(Text, nullable=False)
    dossier_json = Column(JSON, nullable=False, default=dict)
    pdf_report_path = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class VillageResilienceScore(Base):
    """Community disaster drill participation & institutional resilience rating."""

    __tablename__ = "village_resilience_scores"

    id = Column(String(64), primary_key=True, index=True)
    village_id = Column(String(64), ForeignKey("villages.id"), nullable=False, index=True)
    composite_index = Column(Float, nullable=False, default=70.0)  # 0 to 100
    drill_participation_rate = Column(Float, nullable=False, default=0.75)
    volunteer_readiness_score = Column(Float, nullable=False, default=0.8)
    sensor_network_redundancy = Column(Float, nullable=False, default=0.85)
    shelter_accessibility_score = Column(Float, nullable=False, default=0.7)
    grade = Column(String(8), nullable=False, default="A")  # A+, A, B, C, D
    assessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    village = relationship("Village")



