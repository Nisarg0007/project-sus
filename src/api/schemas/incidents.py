"""API schemas for incident list endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IncidentListItem(BaseModel):
    """Incident in the queue list."""

    id: str
    merchant_id: str = Field(..., alias="merchantId")
    date: str
    severity: str
    status: str
    classification: str
    fraud_probability: float = Field(..., alias="fraudProbability")
    confidence: float
    confidence_band: str = Field(..., alias="confidenceBand")
    anomaly_score: float = Field(..., alias="anomalyScore")
    decision_reason: str = Field("", alias="decisionReason")
    anomaly_summary: str = Field("", alias="anomalySummary")
    top_signals: list[str] = Field(default_factory=list, alias="topSignals")
    recommended_action: str = Field("", alias="recommendedAction")

    model_config = {"populate_by_name": True}


class IncidentListResponse(BaseModel):
    """Response for GET /api/v1/incidents"""

    incidents: list[IncidentListItem]
    total: int
