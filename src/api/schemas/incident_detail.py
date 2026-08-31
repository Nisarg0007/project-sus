"""
API schemas for incident detail and workflow management endpoints.

Define request/response models for retrieving incident details,
updating analyst workflow metadata, and viewing status history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------
# Status History
# -----------------------------------------------------------------------

class StatusHistoryEntry(BaseModel):
    """A single status transition in the audit trail."""

    old_status: str = Field(..., description="Previous workflow status")
    new_status: str = Field(..., description="New workflow status")
    changed_by: Optional[str] = Field(
        None, description="Analyst who made the change"
    )
    note: Optional[str] = Field(None, description="Note provided with the change")
    created_at: datetime = Field(..., description="When the change was made")


# -----------------------------------------------------------------------
# Incident Detail Response
# -----------------------------------------------------------------------

class IncidentDetailResponse(BaseModel):
    """Full detail of a persisted incident including ML evidence and workflow."""

    # Identity
    incident_id: str = Field(..., description="Business incident identifier")
    merchant_id: str = Field(..., description="Merchant this incident belongs to")
    date: str = Field(..., description="Date of the triggering event")

    # ML classification (immutable evidence)
    severity: str = Field(..., description="ML severity classification")
    classification: str = Field(..., description="Pipeline classification")
    predicted_cause: Optional[str] = Field(
        None, description="Predicted cause from classifier"
    )

    # ML scores (immutable evidence)
    fraud_probability: float = Field(..., description="Model fraud probability")
    confidence: float = Field(..., description="Model confidence score")
    confidence_band: str = Field(..., description="Confidence band classification")
    anomaly_score: float = Field(..., description="Volume z-score from spike detection")

    # ML evidence (immutable)
    decision_reason: str = Field("", description="Decision rationale")
    anomaly_summary: str = Field("", description="Summary of behavioral anomalies")
    top_signals: list = Field(
        default_factory=list, description="Evidence signals (deserialized JSON)"
    )
    recommended_action: str = Field("", description="System-recommended action")

    # Analyst workflow metadata
    workflow_status: str = Field(
        ..., description="Current analyst workflow status"
    )
    assigned_analyst: Optional[str] = Field(
        None, description="Assigned analyst identifier"
    )
    analyst_notes: Optional[str] = Field(
        None, description="Analyst investigation notes"
    )
    resolution: Optional[str] = Field(
        None, description="Resolution outcome"
    )

    # Timestamps
    created_at: datetime = Field(..., description="When the incident was persisted")
    updated_at: datetime = Field(..., description="When workflow metadata was last changed")

    # Audit trail
    status_history: list[StatusHistoryEntry] = Field(
        default_factory=list, description="Workflow status transition history"
    )


# -----------------------------------------------------------------------
# Incident Update Request
# -----------------------------------------------------------------------

class IncidentUpdateRequest(BaseModel):
    """Request to update an incident's workflow metadata.

    All fields are optional. Only supplied fields are updated.
    Omitted fields remain unchanged.
    """

    workflow_status: Optional[str] = Field(
        None,
        description="New workflow status: open, investigating, resolved, false_positive",
    )
    assigned_analyst: Optional[str] = Field(
        None, description="Analyst to assign (null to clear)"
    )
    analyst_notes: Optional[str] = Field(
        None, description="Investigation notes (null = no change, '' = clear)"
    )
    resolution: Optional[str] = Field(
        None,
        description="Resolution outcome: confirmed_fraud, false_positive, inconclusive",
    )


# -----------------------------------------------------------------------
# Incident List (Persisted) Response
# -----------------------------------------------------------------------

class PersistedIncidentListItem(BaseModel):
    """An incident in the persisted incident queue list."""

    incident_id: str = Field(..., description="Business incident identifier")
    merchant_id: str = Field(..., description="Merchant")
    date: str = Field(..., description="Incident date")
    severity: str = Field(..., description="ML severity classification")
    classification: str = Field(..., description="Pipeline classification")
    workflow_status: str = Field(..., description="Analyst workflow status")
    fraud_probability: float = Field(...)
    confidence: float = Field(...)
    confidence_band: str = Field(...)
    assigned_analyst: Optional[str] = Field(None)
    resolution: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    model_config = {"populate_by_name": True}


class PersistedIncidentListResponse(BaseModel):
    """Paginated list of persisted incidents."""

    incidents: list[PersistedIncidentListItem]
    total: int
    limit: int
    offset: int
