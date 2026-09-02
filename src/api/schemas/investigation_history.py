"""
API schemas for investigation history endpoints.

Define request/response models for retrieving persisted investigations
and their incidents. These are separate from the POST /investigations/run
schemas to allow the history API to evolve independently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Investigation History — List
# ---------------------------------------------------------------------------


class InvestigationListItem(BaseModel):
    """A single investigation in the history list response."""

    investigation_id: str = Field(..., description="Unique investigation identifier")
    status: str = Field(..., description="Investigation run status")
    created_at: datetime = Field(..., description="When the investigation was run")
    total_results: int = Field(..., description="Total merchant-day windows processed")
    spikes_detected: int = Field(..., description="Number of spikes detected")
    fraud_incidents: int = Field(..., description="Fraud-related incidents")
    organic_incidents: int = Field(..., description="Organic traffic incidents")
    review_required: int = Field(..., description="Incidents requiring review")
    baseline_windows: int = Field(..., description="Windows classified as baseline")
    spike_rate: float = Field(..., description="Fraction of windows flagged as spikes")
    processing_note: str = Field("", description="Any pipeline notes")
    dataset_id: Optional[str] = Field(None, description="Source dataset identifier")
    dataset_filename: Optional[str] = Field(None, description="Original dataset filename")
    data_source_type: Optional[str] = Field(None, description="Type of data source (csv, default, etc.)")


class InvestigationListResponse(BaseModel):
    """Paginated list of persisted investigation runs."""

    total: int = Field(..., description="Total number of investigations")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    items: list[InvestigationListItem] = Field(
        default_factory=list, description="Investigation records"
    )


# ---------------------------------------------------------------------------
# Investigation History — Detail
# ---------------------------------------------------------------------------


class PersistedIncidentResponse(BaseModel):
    """A single incident in the investigation detail response."""

    incident_id: str = Field(..., description="Unique incident identifier")
    merchant_id: str = Field(..., description="Merchant this incident belongs to")
    date: str = Field(..., description="Date of the triggering event")
    severity: str = Field(..., description="Severity classification")
    status: str = Field(..., description="Incident operational status")
    classification: str = Field(..., description="Pipeline classification")
    predicted_cause: Optional[str] = Field(
        None, description="Predicted cause from classifier"
    )
    fraud_probability: float = Field(..., description="Model fraud probability")
    confidence: float = Field(..., description="Model confidence score")
    confidence_band: str = Field(..., description="Confidence band classification")
    anomaly_score: float = Field(..., description="Volume z-score from spike detection")
    decision_reason: str = Field("", description="Decision rationale")
    anomaly_summary: str = Field("", description="Summary of behavioral anomalies")
    top_signals: list = Field(
        default_factory=list, description="Evidence signals (deserialized JSON)"
    )
    recommended_action: str = Field("", description="System-recommended action")
    created_at: datetime = Field(..., description="When the incident was persisted")


class InvestigationSummary(BaseModel):
    """Pipeline summary statistics for a persisted investigation."""

    total_results: int = Field(..., description="Total windows processed")
    spikes_detected: int = Field(..., description="Spikes detected")
    fraud_incidents: int = Field(..., description="Fraud incidents")
    organic_incidents: int = Field(..., description="Organic incidents")
    review_required: int = Field(..., description="Review-required incidents")
    baseline_windows: int = Field(..., description="Baseline windows")
    spike_rate: float = Field(..., description="Spike rate")
    processing_note: str = Field("", description="Pipeline processing note")


class InvestigationDetailResponse(BaseModel):
    """Full detail of a persisted investigation including all incidents."""

    investigation_id: str = Field(..., description="Unique investigation identifier")
    status: str = Field(..., description="Run status")
    created_at: datetime = Field(..., description="When the investigation was run")

    # Dataset traceability
    dataset_id: Optional[str] = Field(None, description="Source dataset identifier")
    dataset_filename: Optional[str] = Field(None, description="Original dataset filename")
    data_source_type: Optional[str] = Field(None, description="Type of data source")

    # Input parameters
    transactions_path: str = Field(..., description="Path to transactions CSV")
    window_labels_path: str = Field(..., description="Path to window labels CSV")
    model_path: Optional[str] = Field(None, description="Path to model artifact")
    z_threshold: float = Field(..., description="Z-score threshold used")
    min_history_days: int = Field(..., description="Minimum history days used")
    merchant_filter: Optional[str] = Field(
        None, description="Merchant filter applied"
    )

    # Summary
    summary: InvestigationSummary = Field(
        ..., description="Pipeline summary statistics"
    )

    # Incidents
    incidents: list[PersistedIncidentResponse] = Field(
        default_factory=list, description="All persisted incidents"
    )
