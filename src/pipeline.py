"""
End-to-End SUS Pipeline 🤨

Connects all stages into one production-style orchestration:
1. Feature engineering (raw transactions -> window features)
2. Stage 1 spike detection (statistical anomaly trigger)
3. Stage 2 cause classification (only for detected spikes)
4. Confidence-based triage (high/ambiguous/low confidence bands)
5. Final structured results with decision reasons

Usage:
    python -m src.pipeline

Input:
    data/raw/transactions.csv
    data/raw/window_labels.csv (for feature engineering)
    models/cause_classifier.joblib (pre-trained Stage 2 model)

Output:
    data/processed/pipeline_results.csv
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from src.features import build_window_features
from src.spike_detector import detect_spikes, DEFAULT_Z_THRESHOLD, MIN_HISTORY_DAYS
from src.cause_classifier import (
    get_default_feature_set,
    load_model,
    predict_causes,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Final status values
STATUS_BASELINE = "baseline"
STATUS_ORGANIC_SPIKE = "organic_spike"
STATUS_FRAUD_SPIKE = "fraud_spike"
STATUS_REVIEW_REQUIRED = "review_required"


# ---------------------------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------------------------


def run_pipeline(
    transactions: pd.DataFrame,
    window_labels: pd.DataFrame,
    model_path: Optional[str] = None,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
    min_history_days: int = MIN_HISTORY_DAYS,
) -> pd.DataFrame:
    """
    Run the complete SUS pipeline from raw transactions to final decisions.

    Args:
        transactions: Raw transaction-level data
        window_labels: Window-level labels (merchant_id, date, window_label)
        model_path: Path to pre-trained Stage 2 model. If None, uses default.
        z_threshold: Stage 1 z-score threshold for spike detection
        min_history_days: Minimum historical days required for spike detection

    Returns:
        DataFrame with one row per merchant-day window containing:
        - merchant_id, date (metadata)
        - spike_detected (Stage 1 output)
        - volume_zscore_7d (anomaly score)
        - has_sufficient_history
        - predicted_cause (Stage 2 output, None if no spike)
        - fraud_probability (Stage 2 output, None if no spike)
        - confidence (Stage 2 output, None if no spike)
        - confidence_band (Stage 2 output, None if no spike)
        - final_status (pipeline decision)
        - decision_reason (explanation of the decision)
    """
    # Step 1: Feature engineering
    print("[Pipeline] Step 1: Computing window features...")
    window_features = build_window_features(transactions, window_labels)
    print(f"  Computed {len(window_features)} window features")

    # Step 2: Stage 1 - Spike detection
    print("[Pipeline] Step 2: Detecting spikes...")
    detection_results = detect_spikes(
        window_features,
        z_threshold=z_threshold,
        min_history_days=min_history_days,
    )
    n_spikes = detection_results["is_spike"].sum()
    print(f"  Detected {n_spikes} spikes")

    # Step 3: Stage 2 - Cause classification (only for detected spikes)
    print("[Pipeline] Step 3: Classifying spike causes...")
    feature_cols = get_default_feature_set()

    # Initialize prediction columns
    detection_results["predicted_cause"] = None
    detection_results["fraud_probability"] = np.nan
    detection_results["probability_organic"] = np.nan
    detection_results["confidence"] = np.nan
    detection_results["confidence_band"] = None

    # Load and apply Stage 2 model if we have spikes
    if n_spikes > 0:
        try:
            model_artifact = load_model(model_path)
            model = model_artifact["model"]
            model_feature_cols = model_artifact["feature_cols"]

            # Get spike windows with full features from window_features
            spike_mask = detection_results["is_spike"] == True
            spike_indices = detection_results[spike_mask].index

            # Merge behavioral features from window_features for spike windows
            spike_windows = window_features.loc[spike_indices].copy()

            # Verify all required features exist
            missing_features = set(model_feature_cols) - set(spike_windows.columns)
            if missing_features:
                raise ValueError(f"Missing features for Stage 2: {missing_features}")

            # Get predictions
            predictions = predict_causes(model, spike_windows, model_feature_cols)

            # Merge predictions back
            detection_results.loc[spike_mask, "predicted_cause"] = predictions["predicted_label"].values
            detection_results.loc[spike_mask, "fraud_probability"] = predictions["probability_fraud"].values
            detection_results.loc[spike_mask, "probability_organic"] = predictions["probability_organic"].values
            detection_results.loc[spike_mask, "confidence"] = predictions["confidence"].values
            detection_results.loc[spike_mask, "confidence_band"] = predictions["confidence_band"].values

            print(f"  Classified {n_spikes} spikes")

        except FileNotFoundError:
            print("  WARNING: Stage 2 model not found. Spikes will be flagged for review.")
            detection_results.loc[detection_results["is_spike"] == True, "predicted_cause"] = "unknown"
            detection_results.loc[detection_results["is_spike"] == True, "confidence_band"] = "low_confidence"

    # Step 4: Final status assignment
    print("[Pipeline] Step 4: Assigning final statuses...")
    detection_results["final_status"] = detection_results.apply(
        _assign_final_status, axis=1
    )
    detection_results["decision_reason"] = detection_results.apply(
        _assign_decision_reason, axis=1
    )

    print(f"  Pipeline complete")

    return detection_results


# ---------------------------------------------------------------------------
# Decision Logic
# ---------------------------------------------------------------------------


def _assign_final_status(row: pd.Series) -> str:
    """Assign final status based on pipeline decisions."""
    # No spike detected -> baseline
    if not row["is_spike"]:
        return STATUS_BASELINE

    # Spike detected but no model available
    if row["predicted_cause"] is None or row["predicted_cause"] == "unknown":
        return STATUS_REVIEW_REQUIRED

    # Check confidence band
    confidence_band = row["confidence_band"]

    if confidence_band == "high_confidence":
        # High confidence -> use prediction directly
        if row["predicted_cause"] == "fraud_spike":
            return STATUS_FRAUD_SPIKE
        else:
            return STATUS_ORGANIC_SPIKE

    elif confidence_band == "ambiguous":
        # Ambiguous -> requires review
        return STATUS_REVIEW_REQUIRED

    else:
        # Low confidence -> requires review
        return STATUS_REVIEW_REQUIRED


def _assign_decision_reason(row: pd.Series) -> str:
    """Assign human-readable decision reason."""
    if not row["is_spike"]:
        return "No anomaly detected (z-score below threshold)"

    if row["predicted_cause"] is None or row["predicted_cause"] == "unknown":
        return "Spike detected but Stage 2 model unavailable"

    confidence = row["confidence"]
    confidence_band = row["confidence_band"]

    if confidence_band == "high_confidence":
        return f"High confidence {row['predicted_cause']} (confidence={confidence:.3f})"

    elif confidence_band == "ambiguous":
        return f"Ambiguous classification (confidence={confidence:.3f}), requires review"

    else:
        return f"Low confidence classification (confidence={confidence:.3f}), requires review"


# ---------------------------------------------------------------------------
# Pipeline Summary
# ---------------------------------------------------------------------------


def get_pipeline_summary(results: pd.DataFrame) -> dict:
    """Generate summary statistics from pipeline results."""
    total_windows = len(results)

    status_counts = results["final_status"].value_counts()

    # Spike detection stats
    n_spikes_detected = results["is_spike"].sum()
    spike_rate = n_spikes_detected / total_windows if total_windows > 0 else 0

    # Confidence band distribution (for detected spikes only)
    spike_mask = results["is_spike"] == True
    if spike_mask.sum() > 0:
        confidence_dist = results.loc[spike_mask, "confidence_band"].value_counts()
    else:
        confidence_dist = pd.Series(dtype=int)

    return {
        "total_windows": total_windows,
        "n_baseline": status_counts.get(STATUS_BASELINE, 0),
        "n_organic_spike": status_counts.get(STATUS_ORGANIC_SPIKE, 0),
        "n_fraud_spike": status_counts.get(STATUS_FRAUD_SPIKE, 0),
        "n_review_required": status_counts.get(STATUS_REVIEW_REQUIRED, 0),
        "n_spikes_detected": int(n_spikes_detected),
        "spike_rate": float(spike_rate),
        "confidence_distribution": confidence_dist.to_dict(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(
    transactions_path: str = "data/raw/transactions.csv",
    window_labels_path: str = "data/raw/window_labels.csv",
    model_path: Optional[str] = None,
) -> None:
    """Run the complete SUS pipeline."""
    print("=" * 70)
    print("SUS - END-TO-END PIPELINE")
    print("=" * 70)

    # Load data
    print("\n[1/3] Loading data...")
    transactions = pd.read_csv(transactions_path)
    window_labels = pd.read_csv(window_labels_path)
    print(f"  Transactions: {len(transactions):,}")
    print(f"  Window labels: {len(window_labels)}")

    # Run pipeline
    print("\n[2/3] Running pipeline...")
    results = run_pipeline(
        transactions,
        window_labels,
        model_path=model_path,
    )

    # Save results
    print("\n[3/3] Saving results...")
    output_path = "data/processed/pipeline_results.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    results.to_csv(output_path, index=False)
    print(f"  Saved to: {output_path}")

    # Print summary
    summary = get_pipeline_summary(results)
    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"  Total windows:           {summary['total_windows']}")
    print(f"  Spikes detected:         {summary['n_spikes_detected']}")
    print(f"  Trigger rate:            {summary['spike_rate']:.3f}")
    print(f"\n  Final statuses:")
    print(f"    baseline:              {summary['n_baseline']}")
    print(f"    organic_spike:         {summary['n_organic_spike']}")
    print(f"    fraud_spike:           {summary['n_fraud_spike']}")
    print(f"    review_required:       {summary['n_review_required']}")
    print(f"\n  Confidence bands (detected spikes):")
    for band, count in summary["confidence_distribution"].items():
        print(f"    {band}: {count}")

    # Show sample output
    print(f"\n{'='*60}")
    print("SAMPLE OUTPUT (first 10 rows)")
    print(f"{'='*60}")
    sample_cols = ["merchant_id", "date", "is_spike", "volume_zscore_7d",
                   "predicted_cause", "confidence", "confidence_band", "final_status", "decision_reason"]
    print(results[sample_cols].head(10).to_string(index=False))

    print(f"\n{'='*60}")
    print("Done!")


if __name__ == "__main__":
    main()
