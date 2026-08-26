"""
Activity Service for SUS.

Provides activity event data derived from the ML pipeline.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.incidents import classify_severity
from src.services._helpers import extract_signals, safe_float, safe_str
from src.services.pipeline_data_provider import get_pipeline_results

logger = logging.getLogger(__name__)


def get_activity_events(
    merchant_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """Get activity events derived from pipeline results.

    Returns non-baseline windows as activity events.
    """
    df = get_pipeline_results()

    # Filter to non-baseline (spike events)
    events_df = df[df["final_status"] != "baseline"].copy()

    # Apply filters
    if merchant_id:
        events_df = events_df[events_df["merchant_id"] == merchant_id]

    if date_from:
        events_df = events_df[events_df["date"] >= date_from]

    if date_to:
        events_df = events_df[events_df["date"] <= date_to]

    if status:
        events_df = events_df[events_df["final_status"] == status]

    # Sort by date descending
    events_df = events_df.sort_values("date", ascending=False)

    if limit:
        events_df = events_df.head(limit)

    events = []
    for _, row in events_df.iterrows():
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

        events.append({
            "id": f"EVT-{merchant}-{date_str.replace('-', '')}",
            "merchant_id": merchant,
            "date": date_str,
            "status": final_status,
            "severity": severity_str,
            "transaction_count": int(row.get("transaction_count", 0)),
            "baseline_volume": int(safe_float(row.get("volume_rolling_mean_7d"), 0)),
            "z_score": anomaly_score,
            "fraud_probability": fraud_prob,
            "confidence": confidence_val,
            "confidence_band": confidence_band_str,
            "summary": safe_str(row.get("decision_reason"), ""),
            "top_signals": extract_signals(row),
        })

    return events
