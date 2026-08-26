"""
Shared internal helpers for SUS services.

Avoids duplication of utility functions across merchant_service,
activity_service, incident_service, and investigation_service.
"""

from __future__ import annotations

import pandas as pd


def safe_float(value, default: float = 0.0) -> float:
    """Convert a potentially NaN value to a safe float."""
    if pd.isna(value):
        return default
    return float(value)


def safe_str(value, default: str = "") -> str:
    """Convert a potentially NaN value to a safe string."""
    if pd.isna(value):
        return default
    return str(value)


def extract_signals(row: pd.Series) -> list[str]:
    """Extract top signals from a pipeline row.

    Parses the anomaly_summary field and top_fraud_signal field
    into a list of human-readable signal strings.
    """
    signals: list[str] = []

    summary = safe_str(row.get("anomaly_summary"), "")
    if summary and summary != "Insufficient historical data for comparison":
        for part in summary.split("; "):
            part = part.strip().rstrip(".")
            if part:
                signals.append(part)

    top_fraud = safe_str(row.get("top_fraud_signal"), "")
    if top_fraud:
        signals.append(f"Top fraud contributor: {top_fraud}")

    if not signals:
        signals.append("Anomaly detected via statistical spike detection")

    return signals[:5]
