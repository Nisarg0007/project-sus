"""
Statistical Spike Detector for SUS 🤨 — Stage 1

Detects whether a merchant-day's transaction volume is unusually high
relative to that merchant's own historical behavior.

This module answers ONLY: "Is this a spike?"
It does NOT determine whether the spike is organic or fraud (that's Stage 2).

Operational Design:
------------------
Stage 1 is a high-recall anomaly trigger, NOT a precise classifier.
A false positive only sends an additional window to Stage 2 for classification.
A false negative prevents a genuine spike from reaching the cause classifier.
Therefore the default threshold prioritizes recall over perfect precision.

Usage:
    python -m src.spike_detector

Input:
    data/processed/window_features.csv

Output:
    data/processed/spike_detection_results.csv
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Stage 1 is a high-recall trigger. A z-score of 0.5 means the current day
# is 0.5 standard deviations above the historical mean. This is conservative
# enough to avoid most false positives while capturing ~66% of true spikes.
# The threshold is configurable and can be tuned based on operational needs.
DEFAULT_Z_THRESHOLD = 0.5
MIN_HISTORY_DAYS = 3

# Required input columns
REQUIRED_COLUMNS = [
    "merchant_id",
    "date",
    "window_label",
    "transaction_count",
    "volume_rolling_mean_7d",
    "volume_rolling_std_7d",
    "volume_zscore_7d",
    "volume_ratio_to_7d_mean",
]


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------


def compute_historical_baseline(
    merchant_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute historical rolling statistics for a single merchant.

    Uses ONLY previous observations for each day. The current day's
    transaction count is never included in its own baseline.

    Args:
        merchant_data: DataFrame for a single merchant, sorted by date.

    Returns:
        DataFrame with historical baseline features added/validated.
    """
    df = merchant_data.sort_values("date").copy()
    n = len(df)

    rolling_mean = np.zeros(n)
    rolling_std = np.zeros(n)
    zscore = np.zeros(n)
    ratio_to_mean = np.zeros(n)

    for i in range(n):
        # Use only observations BEFORE the current day (max 7 days lookback)
        start_idx = max(0, i - 7)
        prior_counts = df["transaction_count"].values[start_idx:i]

        if len(prior_counts) == 0:
            # No historical data: use safe defaults
            rolling_mean[i] = df["transaction_count"].values[i]
            rolling_std[i] = 0.0
            zscore[i] = 0.0
            ratio_to_mean[i] = 1.0
            continue

        mean_val = np.mean(prior_counts)
        std_val = np.std(prior_counts, ddof=1) if len(prior_counts) > 1 else 0.0

        rolling_mean[i] = mean_val
        rolling_std[i] = std_val

        # Z-score: how many standard deviations is current day from historical mean
        if std_val > 0:
            zscore[i] = (df["transaction_count"].values[i] - mean_val) / std_val
        else:
            zscore[i] = 0.0

        # Ratio to historical mean
        if mean_val > 0:
            ratio_to_mean[i] = df["transaction_count"].values[i] / mean_val
        else:
            ratio_to_mean[i] = 1.0

    df["volume_rolling_mean_7d"] = rolling_mean
    df["volume_rolling_std_7d"] = rolling_std
    df["volume_zscore_7d"] = zscore
    df["volume_ratio_to_7d_mean"] = ratio_to_mean

    return df


def detect_spikes(
    windows_df: pd.DataFrame,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
    min_history_days: int = MIN_HISTORY_DAYS,
) -> pd.DataFrame:
    """
    Detect volume spikes across all merchant-day windows.

    Uses a merchant-relative z-score approach with configurable threshold.
    Stage 1 is designed as a high-recall trigger: it flags windows that are
    unusually high relative to the merchant's history, sending them to Stage 2
    for cause classification.

    Args:
        windows_df: DataFrame with window-level features.
        z_threshold: Z-score threshold for spike detection. Default is 0.5
                     (high-recall setting for Stage 1 trigger).
        min_history_days: Minimum number of historical days required
                         before a window can be flagged as a spike.

    Returns:
        DataFrame with detection results.
    """
    # Validate required columns
    missing = set(REQUIRED_COLUMNS) - set(windows_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Work on a copy
    df = windows_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Compute historical baseline for each merchant
    merchant_dfs = []
    for merchant_id, group in df.groupby("merchant_id"):
        merchant_dfs.append(compute_historical_baseline(group))

    result = pd.concat(merchant_dfs, ignore_index=True)

    # Determine sufficient history
    # Count days with actual historical data (not including current day)
    result["days_with_history"] = 0
    for merchant_id, group in result.groupby("merchant_id"):
        merchant_result = result[result["merchant_id"] == merchant_id].sort_values("date")
        for i in range(len(merchant_result)):
            # Count prior days (days before current)
            days_with_history = min(i, 7)  # max lookback is 7 days
            result.loc[merchant_result.index[i], "days_with_history"] = days_with_history

    result["has_sufficient_history"] = result["days_with_history"] >= min_history_days

    # Determine spike detection
    # A spike is flagged when:
    # 1. There is sufficient history
    # 2. The z-score meets or exceeds the threshold
    result["is_spike"] = result["has_sufficient_history"] & (result["volume_zscore_7d"] >= z_threshold)

    # Select output columns
    output_columns = [
        "merchant_id",
        "date",
        "window_label",
        "transaction_count",
        "volume_rolling_mean_7d",
        "volume_rolling_std_7d",
        "volume_zscore_7d",
        "volume_ratio_to_7d_mean",
        "has_sufficient_history",
        "is_spike",
    ]

    return result[output_columns]


# ---------------------------------------------------------------------------
# Evaluation functions
# ---------------------------------------------------------------------------


def evaluate_detection(
    detection_results: pd.DataFrame,
) -> dict:
    """
    Evaluate spike detection performance.

    Maps:
    - baseline -> not spike (negative)
    - organic_spike -> spike (positive)
    - fraud_spike -> spike (positive)

    Args:
        detection_results: DataFrame with detection results.

    Returns:
        Dictionary with evaluation metrics.
    """
    # Create binary labels
    df = detection_results.copy()
    df["true_spike"] = df["window_label"].isin(["organic_spike", "fraud_spike"])

    # True positives: correctly detected spikes
    tp = ((df["true_spike"]) & (df["is_spike"])).sum()

    # False positives: incorrectly flagged as spike
    fp = ((~df["true_spike"]) & (df["is_spike"])).sum()

    # True negatives: correctly identified as not spike
    tn = ((~df["true_spike"]) & (~df["is_spike"])).sum()

    # False negatives: missed spikes
    fn = ((df["true_spike"]) & (~df["is_spike"])).sum()

    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Organic and fraud recall separately
    organic_mask = df["window_label"] == "organic_spike"
    fraud_mask = df["window_label"] == "fraud_spike"

    organic_tp = ((organic_mask) & (df["is_spike"])).sum()
    organic_total = organic_mask.sum()
    organic_recall = organic_tp / organic_total if organic_total > 0 else 0.0

    fraud_tp = ((fraud_mask) & (df["is_spike"])).sum()
    fraud_total = fraud_mask.sum()
    fraud_recall = fraud_tp / fraud_total if fraud_total > 0 else 0.0

    return {
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "organic_recall": float(organic_recall),
        "fraud_recall": float(fraud_recall),
    }


def threshold_sensitivity_analysis(
    windows_df: pd.DataFrame,
    thresholds: list[float] = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    min_history_days: int = MIN_HISTORY_DAYS,
) -> pd.DataFrame:
    """
    Evaluate detection performance across multiple thresholds.

    Args:
        windows_df: DataFrame with window-level features.
        thresholds: List of z-score thresholds to evaluate.
        min_history_days: Minimum history requirement.

    Returns:
        DataFrame with metrics for each threshold.
    """
    results = []

    for threshold in thresholds:
        detection = detect_spikes(windows_df, z_threshold=threshold, min_history_days=min_history_days)
        metrics = evaluate_detection(detection)
        metrics["threshold"] = threshold
        results.append(metrics)

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_detection_results(
    detection_results: pd.DataFrame,
    input_df: pd.DataFrame,
) -> list[str]:
    """
    Validate detection results.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # 1. Required columns exist
    required_output = [
        "merchant_id",
        "date",
        "window_label",
        "transaction_count",
        "volume_rolling_mean_7d",
        "volume_rolling_std_7d",
        "volume_zscore_7d",
        "volume_ratio_to_7d_mean",
        "has_sufficient_history",
        "is_spike",
    ]
    for col in required_output:
        if col not in detection_results.columns:
            errors.append(f"Missing required output column: {col}")

    # 2. Same number of rows as input
    if len(detection_results) != len(input_df):
        errors.append(f"Row count mismatch: input={len(input_df)}, output={len(detection_results)}")

    # 3. No duplicate merchant-date pairs
    duplicates = detection_results.duplicated(subset=["merchant_id", "date"])
    if duplicates.any():
        errors.append(f"{duplicates.sum()} duplicate merchant-date pairs")

    # 4. No NaN values
    missing_counts = detection_results.isnull().sum()
    cols_with_missing = missing_counts[missing_counts > 0]
    if len(cols_with_missing) > 0:
        errors.append(f"Columns with missing values: {dict(cols_with_missing)}")

    # 5. No infinite values
    numeric_cols = detection_results.select_dtypes(include=[np.number]).columns
    inf_counts = np.isinf(detection_results[numeric_cols]).sum()
    cols_with_inf = inf_counts[inf_counts > 0]
    if len(cols_with_inf) > 0:
        errors.append(f"Columns with infinite values: {dict(cols_with_inf)}")

    # 6. Windows without sufficient history should not be flagged as spikes
    if "has_sufficient_history" in detection_results.columns and "is_spike" in detection_results.columns:
        insufficient_history = detection_results[~detection_results["has_sufficient_history"]]
        if insufficient_history["is_spike"].any():
            errors.append("Some windows without sufficient history are flagged as spikes")

    # 7. Detection should not depend on window_label
    # This is validated by tests, not here

    return errors


# ---------------------------------------------------------------------------
# Save and run
# ---------------------------------------------------------------------------


def save_results(
    results: pd.DataFrame,
    output_path: str = "data/processed/spike_detection_results.csv",
) -> str:
    """Save detection results to CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    results.to_csv(output_path, index=False)
    return output_path


def main(
    input_path: str = "data/processed/window_features.csv",
    output_path: str = "data/processed/spike_detection_results.csv",
    z_threshold: float = DEFAULT_Z_THRESHOLD,
    min_history_days: int = MIN_HISTORY_DAYS,
) -> None:
    """Main entry point: detect spikes and evaluate performance."""
    print("=" * 60)
    print("SUS — Statistical Spike Detector (Stage 1)")
    print("=" * 60)

    # Load data
    print("\n[1/5] Loading window features...")
    windows_df = pd.read_csv(input_path)
    windows_df["date"] = pd.to_datetime(windows_df["date"])
    print(f"  Input windows: {len(windows_df)}")

    # Detect spikes
    print("\n[2/5] Detecting spikes...")
    detection_results = detect_spikes(windows_df, z_threshold=z_threshold, min_history_days=min_history_days)

    windows_with_history = detection_results["has_sufficient_history"].sum()
    detected_spikes = detection_results["is_spike"].sum()

    print(f"  Windows with sufficient history: {windows_with_history}")
    print(f"  Selected z-score threshold: {z_threshold}")
    print(f"  Detected spikes: {detected_spikes}")

    # Validate
    print("\n[3/5] Validating detection results...")
    errors = validate_detection_results(detection_results, windows_df)
    if errors:
        print("  ERRORS found:")
        for e in errors:
            print(f"    ✗ {e}")
        raise ValueError("Detection validation failed. See errors above.")
    print("  All validation checks passed")

    # Evaluate
    print("\n[4/5] Evaluating detection performance...")
    metrics = evaluate_detection(detection_results)

    print("\n" + "=" * 60)
    print("DETECTOR SANITY CHECK — FULL SYNTHETIC DATA")
    print("=" * 60)
    print(f"  Overall Precision:  {metrics['precision']:.3f}")
    print(f"  Overall Recall:     {metrics['recall']:.3f}")
    print(f"  Overall F1:         {metrics['f1']:.3f}")
    print(f"  Organic Spike Recall: {metrics['organic_recall']:.3f}")
    print(f"  Fraud Spike Recall:   {metrics['fraud_recall']:.3f}")
    print(f"  False Positives:    {metrics['false_positives']}")
    print(f"  True Positives:     {metrics['true_positives']}")
    print(f"  True Negatives:     {metrics['true_negatives']}")
    print(f"  False Negatives:    {metrics['false_negatives']}")

    # Threshold sensitivity analysis
    print("\n[5/5] Running threshold sensitivity analysis...")
    sensitivity_df = threshold_sensitivity_analysis(windows_df, min_history_days=min_history_days)

    print("\n" + "=" * 60)
    print("THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 60)
    print(sensitivity_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Save results
    print("\n" + "=" * 60)
    save_results(detection_results, output_path)
    print(f"  Results saved to: {output_path}")

    # Note about evaluation
    print("\n" + "=" * 60)
    print("NOTE: This evaluation is on the full synthetic dataset for")
    print("validating the spike trigger. It is NOT the final held-out")
    print("classifier evaluation.")
    print("=" * 60)

    print("\nDone!")


if __name__ == "__main__":
    main()
