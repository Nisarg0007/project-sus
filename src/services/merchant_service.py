"""
Merchant Service for SUS.

Provides merchant directory and profile data derived from the ML pipeline.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.incidents import classify_severity
from src.services._helpers import extract_signals, safe_float, safe_str
from src.services.pipeline_data_provider import get_pipeline_results

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Merchant Directory
# ---------------------------------------------------------------------------


def get_merchant_directory() -> list[dict]:
    """Get the merchant directory from pipeline results.

    Returns a list of merchant summary dictionaries.
    """
    df = get_pipeline_results()

    merchants = []
    for merchant_id in sorted(df["merchant_id"].unique()):
        mdf = df[df["merchant_id"] == merchant_id]

        total_windows = len(mdf)
        spikes = int(mdf["is_spike"].sum())
        fraud_count = int((mdf["final_status"] == "fraud_spike").sum())
        organic_count = int((mdf["final_status"] == "organic_spike").sum())
        review_count = int((mdf["final_status"] == "review_required").sum())

        # Risk level derived from incident severity
        if fraud_count >= 2:
            risk_level = "high"
        elif fraud_count >= 1 or review_count >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"

        merchants.append({
            "id": merchant_id,
            "name": merchant_id,
            "dailyVolume": int(mdf["transaction_count"].mean()),
            "riskLevel": risk_level,
            "totalWindows": total_windows,
            "spikesDetected": spikes,
            "fraudCount": fraud_count,
            "organicCount": organic_count,
            "reviewCount": review_count,
        })

    return merchants


# ---------------------------------------------------------------------------
# Merchant Profile
# ---------------------------------------------------------------------------


def get_merchant_profile(merchant_id: str) -> Optional[dict]:
    """Get a detailed merchant profile.

    Returns None if the merchant doesn't exist.
    """
    df = get_pipeline_results()
    mdf = df[df["merchant_id"] == merchant_id]

    if len(mdf) == 0:
        return None

    total_windows = len(mdf)
    spikes = int(mdf["is_spike"].sum())
    fraud_count = int((mdf["final_status"] == "fraud_spike").sum())
    organic_count = int((mdf["final_status"] == "organic_spike").sum())
    review_count = int((mdf["final_status"] == "review_required").sum())

    # Risk posture
    if fraud_count >= 2:
        risk_posture = "high_attention"
        risk_label = "HIGH ATTENTION"
    elif fraud_count >= 1 or review_count >= 2:
        risk_posture = "watch"
        risk_label = "WATCH"
    else:
        risk_posture = "normal"
        risk_label = "NORMAL"

    # Summary narrative
    if fraud_count > 0:
        summary = (
            f"This merchant has generated {fraud_count} fraud-related anomaly "
            f"within the monitored period. {review_count} cases require review."
        )
    elif organic_count > 0:
        summary = (
            f"This merchant shows {organic_count} organic traffic surge(s) "
            f"consistent with legitimate demand patterns."
        )
    else:
        summary = "No unusual behavior detected in the monitored period."

    # Incident history (non-baseline windows)
    incidents = []
    for _, row in mdf[mdf["final_status"] != "baseline"].iterrows():
        fraud_prob = safe_float(row.get("fraud_probability"), 0.0)
        anomaly_score = safe_float(row.get("volume_zscore_7d"), 0.0)
        confidence_val = safe_float(row.get("confidence"), 0.0)
        confidence_band_str = safe_str(row.get("confidence_band"), "low_confidence")
        final_status = row["final_status"]

        severity_str = classify_severity(
            fraud_prob, anomaly_score, confidence_band_str, final_status
        )

        incidents.append({
            "id": f"INC-{merchant_id}-{str(row['date'])[:10].replace('-', '')}",
            "merchant_id": merchant_id,
            "date": str(row["date"])[:10],
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
            "recommended_action": "",
        })

    return {
        "id": merchant_id,
        "name": merchant_id,
        "dailyVolume": int(mdf["transaction_count"].mean()),
        "riskLevel": "high" if fraud_count >= 2 else "medium" if fraud_count >= 1 else "low",
        "riskPosture": risk_posture,
        "riskLabel": risk_label,
        "summary": summary,
        "totalWindows": total_windows,
        "spikesDetected": spikes,
        "fraudCount": fraud_count,
        "organicCount": organic_count,
        "reviewCount": review_count,
        "incidents": incidents,
    }
