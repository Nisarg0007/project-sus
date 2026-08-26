"""
API schemas for investigation endpoints.

These schemas define the HTTP request/response contract. They are separate
from domain models to allow the API layer to evolve independently from
the internal domain representation.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.domain.enums import (
    ConfidenceBand,
    IncidentSeverity,
    IncidentStatus,
    InvestigationStatus,
    PipelineClassification,
)
from src.domain.models import PipelineSummary


# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------

class EvidenceSignal(BaseModel):
    """A single evidence signal in an API response."""

    feature: str
    label: str
    normal_value: float
    current_value: float
    change_percent: float
    signal_type: str


class HealthResponse(BaseModel):
    """Response for GET /health"""

    status: str = Field("healthy", description="Service health status")
    version: str = Field(..., description="Application version")
    pipeline_loaded: bool = Field(
        ..., description="Whether the ML model is loaded and ready"
    )


# ---------------------------------------------------------------------------
# Investigation Request
# ---------------------------------------------------------------------------

class InvestigationRequest(BaseModel):
    """Request to run a pipeline investigation on transaction data.

    Accepts CSV file paths to existing generated data. In production, this
    would accept uploaded files or streaming data.
    """

    transactions_path: str = Field(
        "data/raw/transactions.csv",
        description="Path to the transactions CSV file",
    )
    window_labels_path: str = Field(
        "data/raw/window_labels.csv",
        description="Path to the window labels CSV file",
    )
    model_path: Optional[str] = Field(
        None,
        description="Path to a custom model artifact. Uses default if null.",
    )
    z_threshold: float = Field(
        0.5,
        description="Z-score threshold for spike detection (Stage 1)",
        ge=0.0,
        le=10.0,
    )
    merchant_filter: Optional[str] = Field(
        None,
        description="Filter results to a specific merchant ID",
    )


# ---------------------------------------------------------------------------
# Investigation Response
# ---------------------------------------------------------------------------

class IncidentResponse(BaseModel):
    """Incident data in an API response."""

    id: str
    merchant_id: str
    date: str
    severity: IncidentSeverity
    status: IncidentStatus
    classification: PipelineClassification
    fraud_probability: float
    confidence: float
    confidence_band: ConfidenceBand
    anomaly_score: float
    decision_reason: str
    anomaly_summary: str
    top_signals: list[str]
    recommended_action: str


class InvestigationResponse(BaseModel):
    """Response for POST /investigations/run

    Contains the complete pipeline results formatted for API consumption.
    """

    investigation_id: str = Field(
        ..., description="Unique ID for this investigation run"
    )
    summary: PipelineSummary = Field(
        ..., description="Aggregate pipeline statistics"
    )
    incidents: list[IncidentResponse] = Field(
        default_factory=list,
        description="Generated incidents (fraud + review_required)",
    )
    total_results: int = Field(
        ..., description="Total merchant-day windows processed"
    )
    processing_note: str = Field(
        "",
        description="Any warnings or notes from the pipeline run",
    )
