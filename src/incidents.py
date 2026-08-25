"""
Incident Generation Layer for SUS 🤨

Creates structured incident records for fraud_spike and review_required windows.
Incidents include severity classification, recommended actions, and audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Severity levels
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

# Final statuses that generate incidents
INCIDENT_STATUSES = {"fraud_spike", "review_required"}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Incident:
    """Structured incident record."""
    incident_id: str
    merchant_id: str
    date: str
    severity: str
    final_status: str
    predicted_cause: Optional[str]
    fraud_probability: Optional[float]
    confidence_band: Optional[str]
    anomaly_score: Optional[float]
    decision_reason: str
    anomaly_summary: str
    top_signals: list[str]
    recommended_action: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Severity Classification
# ---------------------------------------------------------------------------


def classify_severity(
    fraud_probability: float,
    anomaly_score: float,
    confidence_band: str,
    final_status: str,
) -> str:
    """
    Deterministic severity classification based on actual outputs.

    Rules (documented in order of priority):

    1. CRITICAL: fraud_spike with high fraud probability (>= 0.9) AND high confidence
    2. HIGH: fraud_spike with moderate fraud probability (>= 0.7) OR high confidence
    3. MEDIUM: fraud_spike with lower probability, OR review_required with high anomaly
    4. LOW: review_required with moderate confidence, or other cases

    Args:
        fraud_probability: Stage 2 fraud probability
        anomaly_score: Stage 1 z-score
        confidence_band: Stage 2 confidence band
        final_status: Pipeline final status

    Returns:
        Severity level string
    """
    # Handle NaN values
    if pd.isna(fraud_probability):
        fraud_probability = 0.0
    if pd.isna(anomaly_score):
        anomaly_score = 0.0

    # Critical: High-confidence fraud with very high probability
    if (final_status == "fraud_spike" and
        fraud_probability >= 0.9 and
        confidence_band == "high_confidence"):
        return SEVERITY_CRITICAL

    # High: Fraud with moderate-to-high probability or high confidence
    if (final_status == "fraud_spike" and
        (fraud_probability >= 0.7 or confidence_band == "high_confidence")):
        return SEVERITY_HIGH

    # Medium: Fraud with lower probability, or review_required with high anomaly
    if final_status == "fraud_spike":
        return SEVERITY_MEDIUM

    if (final_status == "review_required" and
        abs(anomaly_score) >= 2.0):
        return SEVERITY_MEDIUM

    # Low: Review required with moderate confidence
    if final_status == "review_required":
        return SEVERITY_LOW

    return SEVERITY_LOW


# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------


def generate_recommended_action(
    final_status: str,
    severity: str,
    confidence_band: str,
    predicted_cause: Optional[str],
) -> str:
    """
    Generate recommended action based on incident characteristics.

    Actions are tied to actual incident context, not generic templates.
    """
    if final_status == "fraud_spike":
        if severity == SEVERITY_CRITICAL:
            return ("IMMEDIATE ACTION REQUIRED: Review affected transactions, "
                    "investigate abnormal payment/device/IP behavior, and consider "
                    "temporary hold on related accounts.")
        elif severity == SEVERITY_HIGH:
            return ("High priority review: Investigate payment failures, device "
                    "concentration, and IP patterns. Consider temporary restrictions "
                    "pending investigation.")
        else:
            return ("Review recommended: Examine transaction patterns and behavioral "
                    "signals flagged by the classifier.")

    elif final_status == "review_required":
        if confidence_band == "low_confidence":
            return ("Human review required: Anomaly was detected but the cause "
                    "classification confidence is low. Manual investigation needed "
                    "to determine if this is organic or fraud.")
        else:
            return ("Human review recommended: The anomaly was detected but the "
                    "cause classification is ambiguous. Verify whether this represents "
                    "legitimate demand surge or suspicious activity.")

    return "No action required."


# ---------------------------------------------------------------------------
# Incident ID Generation
# ---------------------------------------------------------------------------


def generate_incident_id(merchant_id: str, date: str) -> str:
    """
    Generate deterministic incident ID from merchant_id and date.

    Format: INC-{merchant_id}-{date}
    Example: INC-merchant_001-2025-07-15
    """
    # Clean date string for ID
    date_str = str(date).replace("-", "").replace(" ", "_")[:8]
    return f"INC-{merchant_id}-{date_str}"


# ---------------------------------------------------------------------------
# Top Signals Extraction
# ---------------------------------------------------------------------------


def extract_top_signals(
    anomaly_summary: str,
    top_fraud_signal: str,
    top_organic_signal: str,
    fraud_probability: float,
) -> list[str]:
    """
    Extract the most relevant signals for this incident.
    """
    signals = []

    if anomaly_summary and anomaly_summary != "Insufficient historical data for comparison":
        # Parse anomaly summary into individual signals
        parts = anomaly_summary.split("; ")
        for part in parts:
            part = part.strip().rstrip(".")
            if part:
                signals.append(part)

    if top_fraud_signal:
        signals.append(f"Top fraud contributor: {top_fraud_signal}")

    if not signals:
        signals.append("Anomaly detected via statistical spike detection")

    return signals[:5]  # Limit to top 5 signals


# ---------------------------------------------------------------------------
# Incident Generation
# ---------------------------------------------------------------------------


def create_incident(
    row: pd.Series,
    anomaly_summary: str = "",
    top_fraud_signal: str = "",
    top_organic_signal: str = "",
    explanation_text: str = "",
) -> Optional[Incident]:
    """
    Create an incident record for a pipeline result row.

    Only creates incidents for fraud_spike and review_required statuses.
    Returns None for baseline and organic_spike.

    Args:
        row: Pipeline result row with all fields
        anomaly_summary: Generated anomaly summary
        top_fraud_signal: Top fraud contributing feature
        top_organic_signal: Top organic contributing feature
        explanation_text: Full explanation text

    Returns:
        Incident object or None
    """
    final_status = row.get("final_status", "")

    # Only create incidents for fraud_spike and review_required
    if final_status not in INCIDENT_STATUSES:
        return None

    # Get values with safe defaults
    fraud_probability = row.get("fraud_probability", 0.0)
    if pd.isna(fraud_probability):
        fraud_probability = 0.0

    anomaly_score = row.get("volume_zscore_7d", 0.0)
    if pd.isna(anomaly_score):
        anomaly_score = 0.0

    confidence_band = row.get("confidence_band", "unknown")
    if pd.isna(confidence_band):
        confidence_band = "unknown"

    predicted_cause = row.get("predicted_cause", None)
    if pd.isna(predicted_cause):
        predicted_cause = None

    # Generate incident ID
    incident_id = generate_incident_id(row["merchant_id"], str(row["date"]))

    # Classify severity
    severity = classify_severity(
        fraud_probability, anomaly_score, confidence_band, final_status
    )

    # Generate recommended action
    recommended_action = generate_recommended_action(
        final_status, severity, confidence_band, predicted_cause
    )

    # Extract top signals
    top_signals = extract_top_signals(
        anomaly_summary, top_fraud_signal, top_organic_signal, fraud_probability
    )

    # Decision reason
    decision_reason = row.get("decision_reason", "Unknown")

    return Incident(
        incident_id=incident_id,
        merchant_id=row["merchant_id"],
        date=str(row["date"]),
        severity=severity,
        final_status=final_status,
        predicted_cause=predicted_cause,
        fraud_probability=fraud_probability,
        confidence_band=confidence_band,
        anomaly_score=anomaly_score,
        decision_reason=decision_reason,
        anomaly_summary=anomaly_summary,
        top_signals=top_signals,
        recommended_action=recommended_action,
    )


# ---------------------------------------------------------------------------
# Batch Incident Generation
# ---------------------------------------------------------------------------


def generate_incidents_batch(
    pipeline_results: pd.DataFrame,
    anomaly_summaries: pd.Series = None,
    top_fraud_signals: pd.Series = None,
    explanation_texts: pd.Series = None,
) -> pd.DataFrame:
    """
    Generate incidents for all applicable pipeline results.

    Args:
        pipeline_results: DataFrame with pipeline output
        anomaly_summaries: Optional Series with anomaly summaries
        top_fraud_signals: Optional Series with top fraud signals
        explanation_texts: Optional Series with explanation texts

    Returns:
        DataFrame with incident records
    """
    incidents = []

    for idx, row in pipeline_results.iterrows():
        # Get explanation data if available
        anomaly_summary = ""
        top_fraud_signal = ""
        explanation_text = ""

        if anomaly_summaries is not None and idx in anomaly_summaries.index:
            anomaly_summary = anomaly_summaries[idx]
        if top_fraud_signals is not None and idx in top_fraud_signals.index:
            top_fraud_signal = top_fraud_signals[idx]
        if explanation_texts is not None and idx in explanation_texts.index:
            explanation_text = explanation_texts[idx]

        incident = create_incident(
            row, anomaly_summary, top_fraud_signal, explanation_text=explanation_text
        )

        if incident is not None:
            incidents.append(incident.__dict__)

    return pd.DataFrame(incidents)


# ---------------------------------------------------------------------------
# Incident Summary
# ---------------------------------------------------------------------------


def get_incident_summary(incidents_df: pd.DataFrame) -> dict:
    """Generate summary statistics from incidents."""
    if len(incidents_df) == 0:
        return {"total_incidents": 0}

    severity_dist = incidents_df["severity"].value_counts()
    status_dist = incidents_df["final_status"].value_counts()

    return {
        "total_incidents": len(incidents_df),
        "severity_distribution": severity_dist.to_dict(),
        "status_distribution": status_dist.to_dict(),
        "avg_fraud_probability": incidents_df["fraud_probability"].mean(),
    }
