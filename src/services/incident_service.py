"""
Incident Service for SUS.

Provides incident queue data derived from the ML pipeline.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.incidents import classify_severity, generate_recommended_action
from src.services._helpers import extract_signals, safe_float, safe_str
from src.services.pipeline_data_provider import get_pipeline_results

logger = logging.getLogger(__name__)


def get_incidents(
    merchant_id: Optional[str] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """Get incidents derived from pipeline results.

    Returns incidents for fraud_spike and review_required windows.
    """
    df = get_pipeline_results()

    # Only fraud and review windows produce incidents
    incidents_df = df[df["final_status"].isin(["fraud_spike", "review_required"])].copy()

    # Apply filters
    if merchant_id:
        incidents_df = incidents_df[incidents_df["merchant_id"] == merchant_id]

    if classification:
        incidents_df = incidents_df[incidents_df["final_status"] == classification]

    # Sort by date descending, then by fraud probability
    incidents_df = incidents_df.sort_values(
        ["date", "fraud_probability"], ascending=[False, False]
    )

    if limit:
        incidents_df = incidents_df.head(limit)

    incidents = []
    for _, row in incidents_df.iterrows():
        fraud_prob = safe_float(row.get("fraud_probability"), 0.0)
        anomaly_score = safe_float(row.get("volume_zscore_7d"), 0.0)
        confidence_val = safe_float(row.get("confidence"), 0.0)
        confidence_band_str = safe_str(row.get("confidence_band"), "low_confidence")
        final_status = row["final_status"]
        merchant = row["merchant_id"]
        date_str = str(row["date"])[:10]

        severity_str = classify_severity(
            fraud_prob, anomaly_score, confidence_band_str, final_status
        )

        predicted_cause = row.get("predicted_cause")
        if pd.isna(predicted_cause):
            predicted_cause = None

        recommended_action = generate_recommended_action(
            final_status, severity_str, confidence_band_str, predicted_cause
        )

        # Apply severity filter after computation
        if severity and severity_str != severity:
            continue

        # Apply status filter (all incidents default to "open")
        if status and status != "open":
            continue

        incidents.append({
            "id": f"INC-{merchant}-{date_str.replace('-', '')}",
            "merchant_id": merchant,
            "date": date_str,
            "severity": severity_str,
            "status": "open",
            "classification": final_status,
            "fraud_probability": fraud_prob,
            "confidence": confidence_val,
            "confidence_band": confidence_band_str,
            "anomaly_score": anomaly_score,
            "decision_reason": safe_str(row.get("decision_reason"), ""),
            "anomaly_summary": safe_str(row.get("anomaly_summary"), ""),
            "top_signals": extract_signals(row),
            "recommended_action": recommended_action,
        })

    return incidents
