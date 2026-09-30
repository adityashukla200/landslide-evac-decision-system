"""Pydantic schemas for Dimension 6: AI Copilot & Incident Commander Decision Support."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CopilotActionProposal(BaseModel):
    action_id: str
    action_name: str = Field(..., description="DISPATCH_CELL_BROADCAST, DIVERT_SHELTER, MOBILIZE_AAPDA_MITRA, DISPATCH_SAR")
    description: str
    target_entity_id: str
    payload: Dict[str, Any]
    requires_approval: bool = True
    status: str = "PROPOSED"  # PROPOSED, APPROVED, EXECUTED, REJECTED
    execution_result: Optional[str] = None


class CopilotChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "SESSION_DEFAULT"
    role: str = "INCIDENT_COMMANDER"
    context_village_id: Optional[str] = None


class CopilotChatResponse(BaseModel):
    response_text: str
    sitrep_summary: Dict[str, Any]
    sources_consulted: List[str]
    proposed_actions: List[CopilotActionProposal]
    timestamp: datetime


class CopilotActionExecuteRequest(BaseModel):
    action_id: str
    approved: bool
    officer_notes: Optional[str] = "Approved by Incident Commander"


class CopilotActionExecuteResponse(BaseModel):
    action_id: str
    status: str
    execution_timestamp: datetime
    result_message: str
