"""API Endpoints for Dimension 3: Dynamic Multi-Modal Evacuation Routing & Shelter Balancing."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.schemas.dynamic_routing import (
    RouteNodeSchema,
    RouteEdgeSchema,
    ShelterLiveStatusSchema,
    EvacuationRouteRequest,
    EvacuationRouteResponse,
)
from backend.app.services.routing.dynamic_graph import DynamicEvacuationRouter

router = APIRouter(prefix="/routing", tags=["Dynamic Evacuation Routing"])
evacuation_router_engine = DynamicEvacuationRouter()


class EdgeBlockUpdate(BaseModel):
    edge_id: str
    is_blocked: bool
    block_reason: Optional[str] = None


class ShelterOccupancyUpdate(BaseModel):
    shelter_id: str
    count_change: int


@router.post("/calculate", response_model=EvacuationRouteResponse)
def calculate_dynamic_route(request: EvacuationRouteRequest):
    """Compute dynamic shortest evacuation route under live hazard and shelter occupancy limits."""
    try:
        res = evacuation_router_engine.find_optimal_evacuation(
            origin_village_id=request.origin_village_id,
            evacuee_count=request.evacuee_count,
            preferred_modality=request.preferred_modality,
        )
        return EvacuationRouteResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/shelters", response_model=List[ShelterLiveStatusSchema])
def list_shelters_live():
    """List real-time shelter statuses, capacities, and >90% occupancy diversion flags."""
    return evacuation_router_engine.get_shelter_statuses()


@router.post("/edge/block")
def update_edge_block_status(payload: EdgeBlockUpdate):
    """Block or unblock a road/trail segment in real-time due to flood inundation or landslide."""
    evacuation_router_engine.set_edge_status(
        edge_id=payload.edge_id,
        is_blocked=payload.is_blocked,
        block_reason=payload.block_reason,
    )
    return {"status": "SUCCESS", "edge_id": payload.edge_id, "is_blocked": payload.is_blocked}


@router.post("/shelters/occupancy")
def update_shelter_headcount(payload: ShelterOccupancyUpdate):
    """Update shelter real-time head count."""
    evacuation_router_engine.update_shelter_occupancy(
        shelter_id=payload.shelter_id,
        count_change=payload.count_change,
    )
    return {"status": "SUCCESS", "shelter_id": payload.shelter_id}


@router.get("/network")
def get_evacuation_network():
    """Get the full topology of nodes, edges, and real-time hazard status."""
    return {
        "nodes": evacuation_router_engine.nodes,
        "edges": evacuation_router_engine.edges,
    }
