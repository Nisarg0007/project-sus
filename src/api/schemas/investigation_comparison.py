"""
API schemas for investigation comparison endpoint.

Defines response models for comparing two persisted investigations.
Separate from history schemas to allow independent evolution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------


class MetricComparison(BaseModel):
    """Comparison of a single numeric metric between two investigations."""

    label: str = Field(..., description="Human-readable metric name")
    base_value: float = Field(..., description="Value from the base investigation")
    compare_value: float = Field(..., description="Value from the comparison investigation")
    absolute_change: float = Field(..., description="Compare - base")
    percentage_change: Optional[float] = Field(
        None,
        description="Percentage change (null when base is 0 to avoid division by zero)",
    )


class SummaryComparison(BaseModel):
    """Side-by-side comparison of investigation summary statistics."""

    total_results: MetricComparison
    spikes_detected: MetricComparison
    fraud_incidents: MetricComparison
    organic_incidents: MetricComparison
    review_required: MetricComparison
    baseline_windows: MetricComparison
    spike_rate: MetricComparison


class IncidentChange(BaseModel):
    """Changes detected for an incident present in both investigations."""

    incident_id: str
    merchant_id: str
    severity_changed: bool = False
    old_severity: Optional[str] = None
    new_severity: Optional[str] = None
    classification_changed: bool = False
    old_classification: Optional[str] = None
    new_classification: Optional[str] = None
    fraud_probability_changed: bool = False
    old_fraud_probability: Optional[float] = None
    new_fraud_probability: Optional[float] = None
    confidence_changed: bool = False
    old_confidence: Optional[float] = None
    new_confidence: Optional[float] = None
    anomaly_score_changed: bool = False
    old_anomaly_score: Optional[float] = None
    new_anomaly_score: Optional[float] = None
    predicted_cause_changed: bool = False
    old_predicted_cause: Optional[str] = None
    new_predicted_cause: Optional[str] = None


class IncidentComparison(BaseModel):
    """Grouped incident comparison results."""

    only_in_base: list[str] = Field(
        default_factory=list,
        description="Incident IDs present only in the base investigation",
    )
    only_in_compare: list[str] = Field(
        default_factory=list,
        description="Incident IDs present only in the comparison investigation",
    )
    in_both: list[str] = Field(
        default_factory=list,
        description="Incident IDs present in both investigations",
    )
    changed: list[IncidentChange] = Field(
        default_factory=list,
        description="Incidents with detected field changes",
    )
    unchanged_count: int = Field(
        0,
        description="Number of shared incidents with no detected changes",
    )


class InvestigationMeta(BaseModel):
    """Compact metadata for one investigation in the comparison."""

    investigation_id: str
    created_at: datetime
    status: str


class InvestigationComparisonResponse(BaseModel):
    """Full comparison response for two investigations."""

    base: InvestigationMeta
    compare: InvestigationMeta
    summary: SummaryComparison
    incidents: IncidentComparison
