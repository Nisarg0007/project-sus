"""API schemas for activity endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ActivityEventResponse(BaseModel):
    """Activity event in the API response."""

    id: str
    merchant_id: str = Field(..., alias="merchantId")
    date: str
    status: str
    severity: str
    transaction_count: int = Field(0, alias="transactionCount")
    baseline_volume: int = Field(0, alias="baselineVolume")
    z_score: float = Field(0.0, alias="zScore")
    fraud_probability: float = Field(0.0, alias="fraudProbability")
    confidence: float
    confidence_band: str = Field(..., alias="confidenceBand")
    summary: str = ""
    top_signals: list[str] = Field(default_factory=list, alias="topSignals")

    model_config = {"populate_by_name": True}


class ActivityListResponse(BaseModel):
    """Response for GET /api/v1/activity/events"""

    events: list[ActivityEventResponse]
    total: int
