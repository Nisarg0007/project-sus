"""
Robust Evaluation and Out-of-Fold Predictions for SUS Stage 2 🤨

Implements merchant-grouped leave-one-out cross-validation to produce
honest generalization metrics for the cause classifier.

The primary purpose is honest evaluation, not metric improvement.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANDOM_STATE = 42

# Default fraud decision threshold (probability_fraud >= threshold -> fraud)
DEFAULT_FRAUD_THRESHOLD = 0.50

# Confidence band thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.80
LOW_CONFIDENCE_THRESHOLD = 0.60

# Default cost model
DEFAULT_FALSE_POSITIVE_COST = 1.0
DEFAULT_FALSE_NEGATIVE_COST = 5.0

# Feature columns (same as cause_classifier.py)
FEATURE_COLS = [
    "failed_payment_rate",
    "retry_rate",
    "failed_retry_rate",
    "sku_diversity_ratio",
    "top_sku_share",
    "sku_entropy",
    "device_diversity_ratio",
    "ip_diversity_ratio",
    "ip_entropy",
    "new_customer_share",
    "repeat_customer_share",
    "amount_mean",
    "amount_cv",
    "transaction_count",
    "volume_zscore_7d",
]


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------


def load_spike_windows(
    features_path: str = "data/processed/window_features.csv",
) -> pd.DataFrame:
    """Load only spike windows for Stage 2 evaluation."""
    df = pd.read_csv(features_path)
    df["date"] = pd.to_datetime(df["date"])

    # Filter to spikes only
    df = df[df["window_label"].isin(["organic_spike", "fraud_spike"])].copy()

    # Create target
    df["target"] = (df["window_label"] == "fraud_spike").astype(int)

    return df


# ---------------------------------------------------------------------------
# Leave-One-Merchant-Out Evaluation
# ---------------------------------------------------------------------------


def evaluate_leave_one_merchant_out(
    df: pd.DataFrame,
    feature_cols: list[str] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Perform leave-one-merchant-out cross-validation.

    Each fold:
    - Trains on all merchants except one
    - Tests on the held-out merchant
    - Returns predictions for the held-out merchant

    Returns:
        oof_df: Complete out-of-fold prediction dataframe
        fold_metrics: Per-fold metrics
        aggregate_metrics: Aggregate metrics across all folds
    """
    if feature_cols is None:
        feature_cols = FEATURE_COLS

    X = df[feature_cols].values
    y = df["target"].values
    groups = df["merchant_id"].values

    logo = LeaveOneGroupOut()

    oof_records = []
    fold_metrics_list = []

    for fold_idx, (train_idx, test_idx) in enumerate(logo.split(X, y, groups)):
        # Get train/test data
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Get merchant info
        test_merchant = groups[test_idx][0]  # All test rows are same merchant

        # Train model
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                random_state=RANDOM_STATE,
                max_iter=1000,
            )),
        ])
        pipeline.fit(X_train, y_train)

        # Get predictions
        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]  # Probability of fraud

        # Get identifying info for test rows
        test_df = df.iloc[test_idx]

        # Create OOF records
        for i, idx in enumerate(test_idx):
            prob_organic = 1 - y_proba[i]
            prob_fraud = y_proba[i]
            confidence = max(prob_organic, prob_fraud)

            record = {
                "merchant_id": test_merchant,
                "date": test_df.iloc[i]["date"],
                "true_label": "organic_spike" if y_test[i] == 0 else "fraud_spike",
                "predicted_label": "organic_spike" if y_pred[i] == 0 else "fraud_spike",
                "probability_organic": prob_organic,
                "probability_fraud": prob_fraud,
                "confidence": confidence,
                "confidence_band": _assign_confidence_band(confidence),
                "fold": fold_idx + 1,
            }

            # Add feature values
            for col in feature_cols:
                record[col] = X_test[i, feature_cols.index(col)]

            oof_records.append(record)

        # Calculate fold metrics
        fold_prec = precision_score(y_test, y_pred, zero_division=0)
        fold_rec = recall_score(y_test, y_pred, zero_division=0)
        fold_f1 = f1_score(y_test, y_pred, zero_division=0)
        fold_acc = accuracy_score(y_test, y_pred)

        fold_metrics_list.append({
            "fold": fold_idx + 1,
            "merchant": test_merchant,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "precision": fold_prec,
            "recall": fold_rec,
            "f1": fold_f1,
            "accuracy": fold_acc,
        })

    # Create DataFrames
    oof_df = pd.DataFrame(oof_records)
    fold_metrics = pd.DataFrame(fold_metrics_list)

    # Calculate aggregate metrics
    aggregate_metrics = _calculate_aggregate_metrics(oof_df)

    return oof_df, fold_metrics, aggregate_metrics


def _assign_confidence_band(confidence: float) -> str:
    """Assign confidence band based on thresholds."""
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "high_confidence"
    elif confidence >= LOW_CONFIDENCE_THRESHOLD:
        return "ambiguous"
    else:
        return "low_confidence"


def _calculate_aggregate_metrics(oof_df: pd.DataFrame) -> dict:
    """Calculate aggregate metrics from all OOF predictions."""
    y_true = (oof_df["true_label"] == "fraud_spike").astype(int)
    y_pred = (oof_df["predicted_label"] == "fraud_spike").astype(int)

    # Overall metrics
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    accuracy = accuracy_score(y_true, y_pred)

    # Per-class metrics
    organic_mask_true = y_true == 0
    fraud_mask_true = y_true == 1

    organic_precision = precision_score(y_true, y_pred, pos_label=0, zero_division=0)
    organic_recall = recall_score(y_true, y_pred, pos_label=0, zero_division=0)
    organic_f1 = f1_score(y_true, y_pred, pos_label=0, zero_division=0)

    fraud_precision = precision_score(y_true, y_pred, pos_label=1, zero_division=0)
    fraud_recall = recall_score(y_true, y_pred, pos_label=1, zero_division=0)
    fraud_f1 = f1_score(y_true, y_pred, pos_label=1, zero_division=0)

    # Macro metrics
    macro_precision = (organic_precision + fraud_precision) / 2
    macro_recall = (organic_recall + fraud_recall) / 2
    macro_f1 = (organic_f1 + fraud_f1) / 2

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    # Errors
    fp = ((y_true == 0) & (y_pred == 1)).sum()
    fn = ((y_true == 1) & (y_pred == 0)).sum()

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "organic_precision": organic_precision,
        "organic_recall": organic_recall,
        "organic_f1": organic_f1,
        "fraud_precision": fraud_precision,
        "fraud_recall": fraud_recall,
        "fraud_f1": fraud_f1,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "confusion_matrix": cm,
        "false_positives": int(fp),
        "false_negatives": int(fn),
    }


# ---------------------------------------------------------------------------
# Per-Merchant Metrics
# ---------------------------------------------------------------------------


def calculate_per_merchant_metrics(oof_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate metrics for each merchant separately."""
    results = []

    for merchant in oof_df["merchant_id"].unique():
        merchant_df = oof_df[oof_df["merchant_id"] == merchant]

        y_true = (merchant_df["true_label"] == "fraud_spike").astype(int)
        y_pred = (merchant_df["predicted_label"] == "fraud_spike").astype(int)

        # Handle case where only one class exists in test set
        if len(y_true.unique()) < 2:
            # Can't calculate meaningful metrics
            prec = precision_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
        else:
            prec = precision_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)

        results.append({
            "merchant": merchant,
            "n_windows": len(merchant_df),
            "n_organic": (merchant_df["true_label"] == "organic_spike").sum(),
            "n_fraud": (merchant_df["true_label"] == "fraud_spike").sum(),
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "accuracy": accuracy_score(y_true, y_pred),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Confidence Analysis
# ---------------------------------------------------------------------------


def analyze_confidence_bands(oof_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze model performance by confidence band."""
    results = []

    for band in ["high_confidence", "ambiguous", "low_confidence"]:
        band_df = oof_df[oof_df["confidence_band"] == band]

        if len(band_df) == 0:
            continue

        y_true = (band_df["true_label"] == "fraud_spike").astype(int)
        y_pred = (band_df["predicted_label"] == "fraud_spike").astype(int)

        # Calculate metrics
        acc = accuracy_score(y_true, y_pred)

        # Only calculate class-specific metrics if both classes present
        if len(y_true.unique()) > 1:
            prec = precision_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
        else:
            prec = rec = f1 = 0.0

        results.append({
            "confidence_band": band,
            "n_windows": len(band_df),
            "accuracy": acc,
            "fraud_precision": prec,
            "fraud_recall": rec,
            "fraud_f1": f1,
            "mean_confidence": band_df["confidence"].mean(),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Cost Analysis
# ---------------------------------------------------------------------------


def calculate_cost_over_oof(
    oof_df: pd.DataFrame,
    false_positive_cost: float = DEFAULT_FALSE_POSITIVE_COST,
    false_negative_cost: float = DEFAULT_FALSE_NEGATIVE_COST,
) -> dict:
    """Calculate expected cost across all OOF predictions."""
    y_true = (oof_df["true_label"] == "fraud_spike").astype(int)
    y_pred = (oof_df["predicted_label"] == "fraud_spike").astype(int)

    fp = ((y_true == 0) & (y_pred == 1)).sum()
    fn = ((y_true == 1) & (y_pred == 0)).sum()

    total_cost = (fp * false_positive_cost) + (fn * false_negative_cost)
    avg_cost = total_cost / len(oof_df) if len(oof_df) > 0 else 0

    return {
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "total_cost": float(total_cost),
        "average_cost_per_window": float(avg_cost),
        "fp_cost_per_instance": false_positive_cost,
        "fn_cost_per_instance": false_negative_cost,
    }


def cost_sensitivity_analysis(
    oof_df: pd.DataFrame,
    fp_cost: float = DEFAULT_FALSE_POSITIVE_COST,
    fn_costs: list[float] = None,
) -> pd.DataFrame:
    """Analyze how total cost changes with different FN costs."""
    if fn_costs is None:
        fn_costs = [1.0, 2.0, 3.0, 5.0, 10.0, 20.0]

    results = []
    for fn_cost in fn_costs:
        cost_result = calculate_cost_over_oof(oof_df, fp_cost, fn_cost)
        results.append({
            "false_positive_cost": fp_cost,
            "false_negative_cost": fn_cost,
            "fn_to_fp_ratio": fn_cost / fp_cost,
            "total_cost": cost_result["total_cost"],
            "average_cost": cost_result["average_cost_per_window"],
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Threshold Analysis
# ---------------------------------------------------------------------------


def threshold_analysis(
    oof_df: pd.DataFrame,
    thresholds: list[float] = None,
    false_positive_cost: float = DEFAULT_FALSE_POSITIVE_COST,
    false_negative_cost: float = DEFAULT_FALSE_NEGATIVE_COST,
) -> pd.DataFrame:
    """Evaluate different fraud decision thresholds."""
    if thresholds is None:
        thresholds = [0.30, 0.40, 0.50, 0.60, 0.70]

    results = []

    for threshold in thresholds:
        # Apply threshold
        y_pred = (oof_df["probability_fraud"] >= threshold).astype(int)
        y_true = (oof_df["true_label"] == "fraud_spike").astype(int)

        # Calculate metrics
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        organic_prec = precision_score(y_true, y_pred, pos_label=0, zero_division=0)
        organic_rec = recall_score(y_true, y_pred, pos_label=0, zero_division=0)

        fp = ((y_true == 0) & (y_pred == 1)).sum()
        fn = ((y_true == 1) & (y_pred == 0)).sum()

        cost = (fp * false_positive_cost) + (fn * false_negative_cost)

        results.append({
            "threshold": threshold,
            "fraud_precision": prec,
            "fraud_recall": rec,
            "fraud_f1": f1,
            "organic_precision": organic_prec,
            "organic_recall": organic_rec,
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "total_cost": float(cost),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Brier Score
# ---------------------------------------------------------------------------


def calculate_brier_score(oof_df: pd.DataFrame) -> float:
    """Calculate Brier score for probability calibration assessment."""
    y_true = (oof_df["true_label"] == "fraud_spike").astype(int)
    y_prob = oof_df["probability_fraud"].values

    return brier_score_loss(y_true, y_prob)


# ---------------------------------------------------------------------------
# Error Analysis
# ---------------------------------------------------------------------------


def analyze_errors(oof_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Identify and summarize all OOF errors."""
    # Find errors
    errors = oof_df[oof_df["true_label"] != oof_df["predicted_label"]].copy()

    # Summarize
    summary = {
        "total_errors": len(errors),
        "total_predictions": len(oof_df),
        "error_rate": len(errors) / len(oof_df) if len(oof_df) > 0 else 0,
    }

    if len(errors) > 0:
        # Breakdown by error type
        fp_mask = (errors["true_label"] == "organic_spike") & (errors["predicted_label"] == "fraud_spike")
        fn_mask = (errors["true_label"] == "fraud_spike") & (errors["predicted_label"] == "organic_spike")

        summary["false_positives"] = int(fp_mask.sum())
        summary["false_negatives"] = int(fn_mask.sum())

        # Errors by merchant
        summary["errors_by_merchant"] = errors["merchant_id"].value_counts().to_dict()

        # Errors by confidence band
        summary["errors_by_confidence"] = errors["confidence_band"].value_counts().to_dict()

        # Mean confidence of errors
        summary["mean_error_confidence"] = errors["confidence"].mean()
    else:
        summary["false_positives"] = 0
        summary["false_negatives"] = 0
        summary["errors_by_merchant"] = {}
        summary["errors_by_confidence"] = {}
        summary["mean_error_confidence"] = None

    return errors, summary


# ---------------------------------------------------------------------------
# Main Evaluation
# ---------------------------------------------------------------------------


def main():
    """Run the complete robust evaluation."""
    print("=" * 70)
    print("SUS STAGE 2 -- ROBUST EVALUATION")
    print("=" * 70)

    # Load data
    print("\n[1/8] Loading spike windows...")
    df = load_spike_windows()
    print(f"  Total spike windows: {len(df)}")
    print(f"  Organic: {(df['target'] == 0).sum()}, Fraud: {(df['target'] == 1).sum()}")
    print(f"  Merchants: {df['merchant_id'].nunique()}")

    # Leave-one-merchant-out evaluation
    print("\n[2/8] Running leave-one-merchant-out evaluation...")
    oof_df, fold_metrics, aggregate_metrics = evaluate_leave_one_merchant_out(df)

    # Save OOF predictions
    oof_path = "data/processed/stage2_oof_predictions.csv"
    os.makedirs("data/processed", exist_ok=True)
    oof_df.to_csv(oof_path, index=False)
    print(f"  OOF predictions saved to: {oof_path}")

    # Print aggregate metrics
    print(f"\n{'='*60}")
    print("AGGREGATE OUT-OF-FOLD METRICS")
    print(f"{'='*60}")
    print(f"  Overall Precision:  {aggregate_metrics['precision']:.3f}")
    print(f"  Overall Recall:     {aggregate_metrics['recall']:.3f}")
    print(f"  Overall F1:         {aggregate_metrics['f1']:.3f}")
    print(f"  Overall Accuracy:   {aggregate_metrics['accuracy']:.3f}")
    print(f"\n  Per-Class Metrics:")
    print(f"    Organic Spike:")
    print(f"      Precision: {aggregate_metrics['organic_precision']:.3f}")
    print(f"      Recall:    {aggregate_metrics['organic_recall']:.3f}")
    print(f"      F1:        {aggregate_metrics['organic_f1']:.3f}")
    print(f"    Fraud Spike:")
    print(f"      Precision: {aggregate_metrics['fraud_precision']:.3f}")
    print(f"      Recall:    {aggregate_metrics['fraud_recall']:.3f}")
    print(f"      F1:        {aggregate_metrics['fraud_f1']:.3f}")
    print(f"\n  Macro Metrics:")
    print(f"    Macro Precision: {aggregate_metrics['macro_precision']:.3f}")
    print(f"    Macro Recall:    {aggregate_metrics['macro_recall']:.3f}")
    print(f"    Macro F1:        {aggregate_metrics['macro_f1']:.3f}")
    print(f"\n  Confusion Matrix:")
    cm = aggregate_metrics['confusion_matrix']
    print(f"                 Predicted")
    print(f"                 Organic  Fraud")
    print(f"    Actual Organic  {cm[0][0]:>4}    {cm[0][1]:>4}")
    print(f"           Fraud    {cm[1][0]:>4}    {cm[1][1]:>4}")

    # Per-merchant metrics
    print("\n[3/8] Per-merchant metrics...")
    merchant_metrics = calculate_per_merchant_metrics(oof_df)
    merchant_metrics_path = "data/processed/stage2_merchant_metrics.csv"
    merchant_metrics.to_csv(merchant_metrics_path, index=False)

    print(f"\nPER-MERCHANT F1 TABLE")
    print("-" * 50)
    print(merchant_metrics[["merchant", "n_windows", "n_organic", "n_fraud", "f1", "accuracy"]].to_string(
        index=False, float_format=lambda x: f"{x:.3f}"
    ))

    best_merchant = merchant_metrics.loc[merchant_metrics["f1"].idxmax(), "merchant"]
    worst_merchant = merchant_metrics.loc[merchant_metrics["f1"].idxmin(), "merchant"]
    print(f"\n  Best merchant: {best_merchant} (F1 = {merchant_metrics['f1'].max():.3f})")
    print(f"  Worst merchant: {worst_merchant} (F1 = {merchant_metrics['f1'].min():.3f})")

    # Confidence analysis
    print("\n[4/8] Confidence analysis...")
    confidence_analysis = analyze_confidence_bands(oof_df)

    print(f"\nCONFIDENCE BAND PERFORMANCE")
    print("-" * 50)
    print(confidence_analysis.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Error analysis
    print("\n[5/8] Error analysis...")
    errors, error_summary = analyze_errors(oof_df)

    print(f"\nERROR SUMMARY")
    print("-" * 50)
    print(f"  Total errors: {error_summary['total_errors']} / {error_summary['total_predictions']}")
    print(f"  Error rate:   {error_summary['error_rate']:.3f}")
    print(f"  False positives: {error_summary['false_positives']}")
    print(f"  False negatives: {error_summary['false_negatives']}")

    if error_summary["errors_by_merchant"]:
        print(f"\n  Errors by merchant:")
        for merchant, count in error_summary["errors_by_merchant"].items():
            print(f"    {merchant}: {count}")

    if error_summary["errors_by_confidence"]:
        print(f"\n  Errors by confidence band:")
        for band, count in error_summary["errors_by_confidence"].items():
            print(f"    {band}: {count}")

    if len(errors) > 0:
        print(f"\n  Mean confidence of errors: {error_summary['mean_error_confidence']:.3f}")
    else:
        print(f"\n  No errors to analyze")

    # Cost analysis
    print("\n[6/8] Cost analysis...")
    cost_result = calculate_cost_over_oof(oof_df)

    print(f"\nCOST ANALYSIS (Default Assumptions)")
    print("-" * 50)
    print(f"  False Positive Cost: {cost_result['fp_cost_per_instance']:.1f}")
    print(f"  False Negative Cost: {cost_result['fn_cost_per_instance']:.1f}")
    print(f"  False Positives:     {cost_result['false_positives']}")
    print(f"  False Negatives:     {cost_result['false_negatives']}")
    print(f"  Total Cost:          {cost_result['total_cost']:.1f}")
    print(f"  Average Cost/Window: {cost_result['average_cost_per_window']:.3f}")

    # Cost sensitivity
    cost_sensitivity = cost_sensitivity_analysis(oof_df)
    print(f"\nCOST SENSITIVITY (FN cost varies, FP cost fixed at {DEFAULT_FALSE_POSITIVE_COST})")
    print("-" * 50)
    print(cost_sensitivity.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    # Threshold analysis
    print("\n[7/8] Threshold analysis...")
    threshold_results = threshold_analysis(oof_df)
    threshold_path = "data/processed/stage2_threshold_analysis.csv"
    threshold_results.to_csv(threshold_path, index=False)

    print(f"\nTHRESHOLD SENSITIVITY")
    print("-" * 80)
    print(threshold_results.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Find optimal threshold (minimum cost)
    optimal_row = threshold_results.loc[threshold_results["total_cost"].idxmin()]
    print(f"\n  Optimal threshold (min cost): {optimal_row['threshold']:.2f}")
    print(f"    F1 = {optimal_row['fraud_f1']:.3f}, Cost = {optimal_row['total_cost']:.1f}")

    # Brier score
    print("\n[8/8] Calibration check...")
    brier = calculate_brier_score(oof_df)
    print(f"\nBrier Score: {brier:.4f}")
    if brier < 0.1:
        print("  (Lower is better; < 0.1 indicates reasonable calibration)")
    else:
        print("  (Higher values suggest probabilities may not be well calibrated)")

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL EVALUATION SUMMARY")
    print(f"{'='*70}")

    print(f"\n  AGGREGATE OOF CONFUSION MATRIX:")
    cm = aggregate_metrics['confusion_matrix']
    print(f"                 Predicted")
    print(f"                 Organic  Fraud")
    print(f"    Actual Organic  {cm[0][0]:>4}    {cm[0][1]:>4}")
    print(f"           Fraud    {cm[1][0]:>4}    {cm[1][1]:>4}")

    print(f"\n  AGGREGATE OOF METRICS (PRIMARY):")
    print(f"    Fraud F1:        {aggregate_metrics['fraud_f1']:.3f}")
    print(f"    Organic F1:      {aggregate_metrics['organic_f1']:.3f}")
    print(f"    Macro F1:        {aggregate_metrics['macro_f1']:.3f}")
    print(f"    Accuracy:        {aggregate_metrics['accuracy']:.3f}")

    print(f"\n  PER-MERCHANT PERFORMANCE:")
    print(f"    Best:  {best_merchant} (F1 = {merchant_metrics['f1'].max():.3f})")
    print(f"    Worst: {worst_merchant} (F1 = {merchant_metrics['f1'].min():.3f})")

    print(f"\n  TOTAL FALSE POSITIVES:  {aggregate_metrics['false_positives']}")
    print(f"  TOTAL FALSE NEGATIVES:  {aggregate_metrics['false_negatives']}")
    print(f"  EXPECTED COST:          {cost_result['total_cost']:.1f}")

    print(f"\n  RECOMMENDED THRESHOLD:  {optimal_row['threshold']:.2f}")

    print(f"\n{'='*70}")
    print("METRIC COMPARISON")
    print(f"{'='*70}")
    print(f"\n  PRIMARY GENERALIZATION METRIC:")
    print(f"    Aggregate merchant-aware OOF F1: {aggregate_metrics['f1']:.3f}")
    print(f"\n  OPTIMISTIC RANDOM-CV METRIC (for reference only):")
    print(f"    Stratified 5-fold CV F1: ~0.989")
    print(f"    (This is overly optimistic due to merchant information leakage)")
    print(f"\n  SPECIFIC HOLDOUT DEMONSTRATION:")
    print(f"    merchant_002 + merchant_006 holdout F1: 1.000")
    print(f"    (This was one favorable split, not representative of generalization)")

    print(f"\n  DO NOT claim the model is production-ready.")
    print(f"  The honest generalization metric is the aggregate OOF result.")

    print(f"\n{'='*70}")
    print("Done!")


if __name__ == "__main__":
    main()
