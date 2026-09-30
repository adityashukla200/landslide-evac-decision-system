"""API Endpoints for Dimension 6: AI Disaster Copilot & Human-in-the-Loop Decision Support."""

from fastapi import APIRouter, HTTPException, Depends
from backend.app.schemas.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotActionExecuteRequest,
    CopilotActionExecuteResponse,
)
from backend.app.services.copilot.rag_assistant import IncidentCommanderCopilot

router = APIRouter(prefix="/copilot", tags=["AI Disaster Copilot"])
copilot_engine = IncidentCommanderCopilot()


@router.post("/chat", response_model=CopilotChatResponse)
def chat_with_disaster_copilot(request: CopilotChatRequest):
    """Query the AI Copilot for real-time situational awareness and tactical action proposals."""
    res = copilot_engine.process_query(
        message=request.message,
        role=request.role,
        context_village_id=request.context_village_id,
    )
    return CopilotChatResponse(**res)


@router.post("/actions/execute", response_model=CopilotActionExecuteResponse)
def execute_copilot_proposed_action(request: CopilotActionExecuteRequest):
    """Confirm or reject a tool action proposed by the Copilot (Human-in-the-loop)."""
    try:
        res = copilot_engine.execute_action(
            action_id=request.action_id,
            approved=request.approved,
            notes=request.officer_notes or "Authorized by Commander",
        )
        return CopilotActionExecuteResponse(**res)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sitrep")
def get_live_sitrep():
    """Retrieve live Situation Report (SITREP) synthesized from basin telemetry."""
    return copilot_engine.generate_sitrep()
