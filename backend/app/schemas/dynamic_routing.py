"""Pydantic schemas for Dimension 3: Dynamic Evacuation Routing & Shelter Capacity Balancing."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RouteNodeSchema(BaseModel):
    node_id: str
    name: str
    latitude: float
    longitude: float
    node_type: str = Field(..., description="VILLAGE, JUNCTION, SHELTER, HELIPAD")


class RouteEdgeSchema(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    modality: str = Field(..., description="PEDESTRIAN_TRAIL, ROAD_4X4, HELICOPTER_AIR")
    distance_meters: float
    base_time_minutes: float
    is_blocked: bool = False
    block_reason: Optional[str] = None
    hazard_score: float = 0.0


class ShelterLiveStatusSchema(BaseModel):
    shelter_id: str
    name: str
    village_id: Optional[str] = None
    latitude: float
    longitude: float
    total_capacity: int
    current_occupancy: int
    occupancy_pct: float
    is_accepting: bool = True
    elevation_m: float = 2400.0


class EvacuationRouteRequest(BaseModel):
    origin_village_id: str
    evacuee_count: int = 45
    preferred_modality: str = Field(default="MULTIMODAL", description="PEDESTRIAN, ROAD_4X4, HELICOPTER, MULTIMODAL")
    require_medical_facility: bool = False


class EvacuationWaypoint(BaseModel):
    node_id: str
    name: str
    latitude: float
    longitude: float
    step_description: str
    cumulative_distance_m: float
    cumulative_time_min: float


class EvacuationRouteResponse(BaseModel):
    path_found: bool
    origin_village_id: str
    destination_shelter_id: str
    destination_shelter_name: str
    modality: str
    waypoints: List[EvacuationWaypoint]
    total_distance_m: float
    total_time_minutes: float
    bottlenecks_avoided: List[str]
    shelter_rebalanced: bool
    rebalancing_reason: Optional[str] = None
