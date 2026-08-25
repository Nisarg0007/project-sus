"""
Stage 2 -- Cause Classifier for SUS 🤨

Distinguishes organic spikes from fraud spikes using behavioral pattern features.

This module is designed for honest evaluation:
- Uses merchant-aware train/test splits to measure true generalization
- Reports per-class metrics to avoid hiding poor performance
- Includes confidence bands for future Stage 3 LLM triage
- Supports cost-weighted evaluation for operational decision-making

Usage:
    python -m src.cause_classifier

Input:
    data/processed/window_features.csv

Output:
    Trained model artifacts in models/
    Evaluation metrics printed to console
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANDOM_STATE = 42

# Confidence band thresholds for Stage 3 triage
HIGH_CONFIDENCE_THRESHOLD = 0.80
LOW_CONFIDENCE_THRESHOLD = 0.60

# Default cost model (simulation assumptions for hackathon)
DEFAULT_FALSE_POSITIVE_COST = 1.0  # Legitimate spike flagged as fraud
DEFAULT_FALSE_NEGATIVE_COST = 5.0  # Fraud spike missed (higher cost)

# Metadata columns to exclude from features
METADATA_COLUMNS = ["merchant_id", "date", "window_label", "window_label_original"]

# Model artifact path
MODEL_DIR = "models"
MODEL_FILENAME = "cause_classifier.joblib"


# ---------------------------------------------------------------------------
# Feature Selection
# ---------------------------------------------------------------------------

def get_default_feature_set() -> list[str]:
    """
    Return the approved feature set for Stage 2 cause classification.

    Features are selected based on adversarial audit findings:
    - Removed mathematically redundant features (e.g., success_rate vs failed_payment_rate)
    - Removed duplicate retry signals
    - Reduced redundant amount statistics
    - Kept features representing genuinely different behavioral patterns

    Target: compact, interpretable feature set (~15-20 features).
    """
    features = [
        # Payment behavior (strongest signal from audit)
        "failed_payment_rate",      # Primary payment failure indicator
        "retry_rate",               # Retry attempt behavior
        "failed_retry_rate",        # Failed retry specifically

        # SKU diversity and concentration
        "sku_diversity_ratio",      # How diverse is the SKU usage
        "top_sku_share",            # Concentration on top SKU
        "sku_entropy",              # Shannon entropy of SKU distribution

        # Device and IP concentration
        "device_diversity_ratio",   # Device spread
        "ip_diversity_ratio",       # IP spread
        "ip_entropy",               # IP distribution entropy

        # Customer behavior
        "new_customer_share",       # Proportion of new customers
        "repeat_customer_share",    # Proportion of repeat customers

        # Transaction amounts
        "amount_mean",              # Average transaction value
        "amount_cv",                # Coefficient of variation (relative spread)

        # Volume (limited set - volume alone is insufficient per SUS hypothesis)
        "transaction_count",        # Raw volume
        "volume_zscore_7d",         # Historical context
    ]

    return features


# ---------------------------------------------------------------------------
# Data Preparation
# ---------------------------------------------------------------------------

def prepare_stage2_data(
    features_path: str = "data/processed/window_features.csv",
) -> tuple[pd.DataFrame, list[str]]:
    """
    Load and prepare Stage 2 dataset.

    Returns only organic_spike and fraud_spike windows with:
    - Original window_label for reporting
    - Numeric target (organic=0, fraud=1)
    - Approved behavioral features

    Returns:
        df: DataFrame with Stage 2 windows
        feature_cols: List of approved feature columns
    """
    df = pd.read_csv(features_path)
    df["date"] = pd.to_datetime(df["date"])

    # Filter to spike windows only
    spike_mask = df["window_label"].isin(["organic_spike", "fraud_spike"])
    df = df[spike_mask].copy()

    # Create target
    df["target"] = (df["window_label"] == "fraud_spike").astype(int)

    # Get approved features
    feature_cols = get_default_feature_set()

    # Validate features exist
    missing = set(feature_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    return df, feature_cols


# ---------------------------------------------------------------------------
# Train/Test Split
# ---------------------------------------------------------------------------

def split_by_merchant(
    df: pd.DataFrame,
    feature_cols: list[str],
    test_size: float = 0.25,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, list[str], list[str]]:
    """
    Split data by merchant to ensure no merchant overlap between train and test.

    This provides honest generalization metrics by testing on merchants
    the model has never seen.

    Returns:
        X_train, X_test, y_train, y_test, train_merchants, test_merchants
    """
    groups = df["merchant_id"].values
    y = df["target"].values

    # Use GroupShuffleSplit for merchant-aware splitting
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=random_state,
    )

    train_idx, test_idx = next(splitter.split(df, y, groups))

    # Extract splits
    train_merchants = sorted(df.iloc[train_idx]["merchant_id"].unique())
    test_merchants = sorted(df.iloc[test_idx]["merchant_id"].unique())

    # Validate no overlap
    overlap = set(train_merchants) & set(test_merchants)
    if overlap:
        raise ValueError(f"Merchant overlap detected: {overlap}")

    X_train = df.iloc[train_idx][feature_cols].reset_index(drop=True)
    X_test = df.iloc[test_idx][feature_cols].reset_index(drop=True)
    y_train = pd.Series(y[train_idx], name="target").reset_index(drop=True)
    y_test = pd.Series(y[test_idx], name="target").reset_index(drop=True)

    return X_train, X_test, y_train, y_test, train_merchants, test_merchants


# ---------------------------------------------------------------------------
# Model Training
# ---------------------------------------------------------------------------

def train_cause_classifier(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_type: str = "logistic_regression",
) -> Pipeline:
    """
    Train a cause classifier on the training data.

    Args:
        X_train: Training features
        y_train: Training labels
        model_type: 'logistic_regression' or 'dummy'

    Returns:
        Trained sklearn Pipeline
    """
    if model_type == "dummy":
        model = DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)
        pipeline = Pipeline([("classifier", model)])
    else:
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                random_state=RANDOM_STATE,
                max_iter=1000,
                C=1.0,
                class_weight=None,
            )),
        ])

    pipeline.fit(X_train, y_train)
    return pipeline


# ---------------------------------------------------------------------------
# Prediction and Confidence
# ---------------------------------------------------------------------------

def predict_causes(
    model: Pipeline,
    df: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """
    Generate predictions with confidence scores for Stage 2 windows.

    Returns DataFrame with original identifying columns plus:
    - predicted_label
    - probability_organic
    - probability_fraud
    - confidence
    - confidence_band

    Args:
        model: Trained sklearn Pipeline
        df: DataFrame with Stage 2 windows
        feature_cols: Feature columns used by the model

    Returns:
        DataFrame with predictions
    """
    # Get identifying columns
    id_cols = ["merchant_id", "date"]
    if "window_label" in df.columns:
        id_cols.append("window_label")

    result = df[id_cols].copy()

    # Get features
    X = df[feature_cols]

    # Get predictions
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)

    # Add predictions
    result["predicted_label"] = ["organic_spike" if p == 0 else "fraud_spike" for p in y_pred]
    result["probability_organic"] = y_proba[:, 0]
    result["probability_fraud"] = y_proba[:, 1]

    # Calculate confidence
    result["confidence"] = np.maximum(result["probability_organic"], result["probability_fraud"])

    # Assign confidence bands
    result["confidence_band"] = result["confidence"].apply(_assign_confidence_band)

    # Add feature values for audit trail
    for col in feature_cols:
        result[col] = df[col].values

    return result


def _assign_confidence_band(confidence: float) -> str:
    """Assign confidence band based on thresholds."""
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "high_confidence"
    elif confidence >= LOW_CONFIDENCE_THRESHOLD:
        return "ambiguous"
    else:
        return "low_confidence"


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_classifier(
    y_true: pd.Series,
    y_pred: pd.Series,
    class_names: list[str] = None,
) -> dict:
    """
    Evaluate classifier performance with comprehensive metrics.

    Returns dictionary with all required metrics.
    """
    if class_names is None:
        class_names = ["organic_spike", "fraud_spike"]

    # Basic metrics
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    accuracy = accuracy_score(y_true, y_pred)

    # Per-class metrics
    report = classification_report(y_true, y_pred, target_names=class_names, output_dict=True)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "confusion_matrix": cm,
        "classification_report": report,
        "organic_precision": report["organic_spike"]["precision"],
        "organic_recall": report["organic_spike"]["recall"],
        "organic_f1": report["organic_spike"]["f1-score"],
        "fraud_precision": report["fraud_spike"]["precision"],
        "fraud_recall": report["fraud_spike"]["recall"],
        "fraud_f1": report["fraud_spike"]["f1-score"],
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
        "macro_f1": report["macro avg"]["f1-score"],
    }


# ---------------------------------------------------------------------------
# Cost-Weighted Evaluation
# ---------------------------------------------------------------------------

@dataclass
class CostModel:
    """Cost model for false positive and false negative evaluation."""
    false_positive_cost: float = DEFAULT_FALSE_POSITIVE_COST
    false_negative_cost: float = DEFAULT_FALSE_NEGATIVE_COST

    def __post_init__(self):
        """Validate cost parameters."""
        if self.false_positive_cost < 0:
            raise ValueError("false_positive_cost must be non-negative")
        if self.false_negative_cost < 0:
            raise ValueError("false_negative_cost must be non-negative")


def calculate_expected_cost(
    y_true: pd.Series,
    y_pred: pd.Series,
    cost_model: CostModel = None,
) -> dict:
    """
    Calculate expected cost based on false positives and false negatives.

    Args:
        y_true: True labels (0=organic, 1=fraud)
        y_pred: Predicted labels (0=organic, 1=fraud)
        cost_model: CostModel with costs for FP and FN

    Returns:
        Dictionary with cost metrics
    """
    if cost_model is None:
        cost_model = CostModel()

    # Calculate errors
    fp_mask = (y_true == 0) & (y_pred == 1)  # Organic misclassified as fraud
    fn_mask = (y_true == 1) & (y_pred == 0)  # Fraud misclassified as organic

    fp_count = fp_mask.sum()
    fn_count = fn_mask.sum()

    # Calculate costs
    total_cost = (fp_count * cost_model.false_positive_cost +
                  fn_count * cost_model.false_negative_cost)

    avg_cost = total_cost / len(y_true) if len(y_true) > 0 else 0

    return {
        "false_positives": int(fp_count),
        "false_negatives": int(fn_count),
        "total_cost": float(total_cost),
        "average_cost_per_window": float(avg_cost),
        "fp_cost_per_instance": cost_model.false_positive_cost,
        "fn_cost_per_instance": cost_model.false_negative_cost,
    }


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

def generate_audit_trail(
    predictions_df: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """
    Generate prediction-level audit records for human review.

    Includes all identifying information, predictions, probabilities,
    confidence bands, and feature values used for each prediction.
    """
    audit_cols = [
        "merchant_id",
        "date",
        "window_label",  # True label if available
        "predicted_label",
        "probability_organic",
        "probability_fraud",
        "confidence",
        "confidence_band",
    ] + feature_cols

    # Select available columns
    available_cols = [c for c in audit_cols if c in predictions_df.columns]

    return predictions_df[available_cols].copy()


# ---------------------------------------------------------------------------
# Model Save/Load
# ---------------------------------------------------------------------------

def save_model(
    model: Pipeline,
    feature_cols: list[str],
    metadata: dict = None,
    output_dir: str = MODEL_DIR,
) -> str:
    """
    Save trained model and associated metadata.

    Args:
        model: Trained sklearn Pipeline
        feature_cols: Feature columns used by the model
        metadata: Additional metadata to save
        output_dir: Directory to save model artifacts

    Returns:
        Path to saved model file
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, MODEL_FILENAME)

    artifact = {
        "model": model,
        "feature_cols": feature_cols,
        "metadata": metadata or {},
    }

    joblib.dump(artifact, filepath)
    return filepath


def load_model(filepath: str = None) -> dict:
    """
    Load trained model and associated metadata.

    Returns:
        Dictionary with 'model', 'feature_cols', and 'metadata'
    """
    if filepath is None:
        filepath = os.path.join(MODEL_DIR, MODEL_FILENAME)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Model file not found: {filepath}")

    return joblib.load(filepath)


# ---------------------------------------------------------------------------
# Main Experiment
# ---------------------------------------------------------------------------

def main(
    features_path: str = "data/processed/window_features.csv",
) -> None:
    """Run the complete Stage 2 cause classifier experiment."""
    print("=" * 70)
    print("SUS STAGE 2 -- CAUSE CLASSIFIER")
    print("=" * 70)

    # Step 1: Prepare data
    print("\n[1/7] Preparing Stage 2 data...")
    df, feature_cols = prepare_stage2_data(features_path)

    print(f"\nSTAGE 2 DATASET")
    print("-" * 50)
    print(f"  Total windows:  {len(df)}")
    print(f"  Organic spikes: {(df['target'] == 0).sum()}")
    print(f"  Fraud spikes:   {(df['target'] == 1).sum()}")
    print(f"  Features:       {len(feature_cols)}")

    # Step 2: Split by merchant
    print("\n[2/7] Splitting by merchant...")
    X_train, X_test, y_train, y_test, train_merchants, test_merchants = split_by_merchant(
        df, feature_cols
    )

    print(f"\nMERCHANT-AWARE SPLIT")
    print("-" * 50)
    print(f"  Train merchants: {train_merchants}")
    print(f"  Test merchants:  {test_merchants}")
    print(f"  Train size: {len(X_train)} (organic: {(y_train == 0).sum()}, fraud: {(y_train == 1).sum()})")
    print(f"  Test size:  {len(X_test)} (organic: {(y_test == 0).sum()}, fraud: {(y_test == 1).sum()})")

    # Step 3: Train validation models
    print("\n[3/7] Training validation models...")
    print("\nVALIDATION ON TRAINING MERCHANTS")
    print("-" * 50)

    # DummyClassifier baseline
    dummy_model = train_cause_classifier(X_train, y_train, model_type="dummy")
    dummy_pred = dummy_model.predict(X_train)
    dummy_metrics = evaluate_classifier(y_train, dummy_pred)
    print(f"  DummyClassifier (train): F1 = {dummy_metrics['f1']:.3f}")

    # LogisticRegression
    lr_model = train_cause_classifier(X_train, y_train, model_type="logistic_regression")
    lr_pred = lr_model.predict(X_train)
    lr_metrics = evaluate_classifier(y_train, lr_pred)
    print(f"  LogisticRegression (train): F1 = {lr_metrics['f1']:.3f}")

    # Step 4: Train final model
    print("\n[4/7] Training final model on all training data...")
    final_model = train_cause_classifier(X_train, y_train, model_type="logistic_regression")

    # Step 5: Evaluate on held-out test merchants
    print("\n[5/7] Evaluating on held-out test merchants...")
    test_pred = final_model.predict(X_test)
    test_proba = final_model.predict_proba(X_test)
    test_metrics = evaluate_classifier(y_test, test_pred)

    print(f"\n{'='*50}")
    print("FINAL HELD-OUT MERCHANT METRICS")
    print(f"{'='*50}")
    print(f"  Overall Precision:  {test_metrics['precision']:.3f}")
    print(f"  Overall Recall:     {test_metrics['recall']:.3f}")
    print(f"  Overall F1:         {test_metrics['f1']:.3f}")
    print(f"  Overall Accuracy:   {test_metrics['accuracy']:.3f}")
    print(f"\n  Per-Class Metrics:")
    print(f"    Organic Spike:")
    print(f"      Precision: {test_metrics['organic_precision']:.3f}")
    print(f"      Recall:    {test_metrics['organic_recall']:.3f}")
    print(f"      F1:        {test_metrics['organic_f1']:.3f}")
    print(f"    Fraud Spike:")
    print(f"      Precision: {test_metrics['fraud_precision']:.3f}")
    print(f"      Recall:    {test_metrics['fraud_recall']:.3f}")
    print(f"      F1:        {test_metrics['fraud_f1']:.3f}")
    print(f"\n  Macro Metrics:")
    print(f"    Macro Precision: {test_metrics['macro_precision']:.3f}")
    print(f"    Macro Recall:    {test_metrics['macro_recall']:.3f}")
    print(f"    Macro F1:        {test_metrics['macro_f1']:.3f}")
    print(f"\n  Confusion Matrix:")
    print(f"                 Predicted")
    print(f"                 Organic  Fraud")
    print(f"    Actual Organic  {test_metrics['confusion_matrix'][0][0]:>4}    {test_metrics['confusion_matrix'][0][1]:>4}")
    print(f"           Fraud    {test_metrics['confusion_matrix'][1][0]:>4}    {test_metrics['confusion_matrix'][1][1]:>4}")

    # Step 6: Cost analysis
    print("\n[6/7] Cost analysis...")
    cost_model = CostModel()
    cost_result = calculate_expected_cost(y_test, test_pred, cost_model)

    print(f"\nCOST ANALYSIS (Simulation Assumptions)")
    print("-" * 50)
    print(f"  False Positive Cost: {cost_model.false_positive_cost:.1f} (organic flagged as fraud)")
    print(f"  False Negative Cost: {cost_model.false_negative_cost:.1f} (fraud missed)")
    print(f"  False Positives:     {cost_result['false_positives']}")
    print(f"  False Negatives:     {cost_result['false_negatives']}")
    print(f"  Total Cost:          {cost_result['total_cost']:.1f}")
    print(f"  Average Cost/Window: {cost_result['average_cost_per_window']:.3f}")

    # Confidence bands
    test_df = df.iloc[y_test.index]
    predictions_df = predict_causes(final_model, test_df, feature_cols)

    confidence_dist = predictions_df["confidence_band"].value_counts()
    print(f"\nCONFIDENCE BANDS (Test Set)")
    print("-" * 50)
    print(f"  high_confidence (>= {HIGH_CONFIDENCE_THRESHOLD}): {(confidence_dist.get('high_confidence', 0))}")
    print(f"  ambiguous ({LOW_CONFIDENCE_THRESHOLD} - {HIGH_CONFIDENCE_THRESHOLD}): {(confidence_dist.get('ambiguous', 0))}")
    print(f"  low_confidence (< {LOW_CONFIDENCE_THRESHOLD}): {(confidence_dist.get('low_confidence', 0))}")

    # Step 7: Save model
    print("\n[7/7] Saving model...")
    metadata = {
        "feature_cols": feature_cols,
        "train_merchants": train_merchants,
        "test_merchants": test_merchants,
        "held_out_f1": test_metrics["f1"],
        "cost_model": {
            "false_positive_cost": cost_model.false_positive_cost,
            "false_negative_cost": cost_model.false_negative_cost,
        },
    }
    model_path = save_model(final_model, feature_cols, metadata)
    print(f"  Model saved to: {model_path}")

    # Generate audit trail
    audit_df = generate_audit_trail(predictions_df, feature_cols)
    audit_path = os.path.join("data/processed", "stage2_audit_trail.csv")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    audit_df.to_csv(audit_path, index=False)
    print(f"  Audit trail saved to: {audit_path}")

    # Final summary
    print(f"\n{'='*50}")
    print("FINAL SUMMARY")
    print(f"{'='*50}")
    print(f"\n  Feature Set ({len(feature_cols)} features):")
    print(f"    {feature_cols}")
    print(f"\n  Train Merchants: {train_merchants}")
    print(f"  Test Merchants:  {test_merchants}")
    print(f"\n  Held-Out Merchant F1: {test_metrics['f1']:.3f}")
    print(f"  (This is the honest generalization metric, NOT cross-validation)")
    print(f"\n  CAVEATS:")
    print(f"  - Dataset is small (109 spike windows)")
    print(f"  - Generalization to unseen merchants is harder than random splits")
    print(f"  - One merchant group may perform significantly differently")
    print(f"  - Results are on synthetic data and may not reflect real-world performance")

    print(f"\n{'='*50}")
    print("Done!")


if __name__ == "__main__":
    main()
