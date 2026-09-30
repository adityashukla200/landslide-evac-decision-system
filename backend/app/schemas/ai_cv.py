"""Pydantic schemas for Computer Vision hazard analysis on citizen media."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CVAnalysisResult(BaseModel):
    """Result of automated Computer Vision analysis on photo or video."""

    report_id: str
    media_type: str = Field(..., description="photo or video")
    water_fraction: float = Field(..., ge=0.0, le=1.0, description="Estimated fraction of image covered by floodwater")
    estimated_depth_m: Optional[float] = Field(None, ge=0.0, description="Estimated flood stage depth in meters")
    debris_velocity_ms: Optional[float] = Field(None, ge=0.0, description="Estimated debris flow or surface water velocity in m/s")
    is_false_alarm: bool = Field(..., description="True if AI classifies the image as not showing active flooding/landslide")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    model_version: str = Field(..., description="Identifier of the CV model pipeline used")
    features: Dict[str, Any] = Field(default_factory=dict, description="Detailed geometric features (bounding boxes, contours, flow vectors)")
    processed_at: datetime


class CVAnalysisTriggerRequest(BaseModel):
    """Request to trigger or re-run CV analysis on a citizen report."""

    force_recompute: bool = Field(False, description="Recompute even if already processed")
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold for classification")
