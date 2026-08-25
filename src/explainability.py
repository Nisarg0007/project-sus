"""
Explainability Layer for SUS 🤨

Provides human-readable explanations for pipeline decisions by analyzing:
- Feature deviations from merchant historical baselines
- Model contribution analysis from LogisticRegression coefficients
- Structured explanation objects for each suspicious window

All explanations are derived from actual computed features and model outputs.
No fabricated or generic explanations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.cause_classifier import get_default_feature_set, load_model


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Features to analyze for deviation
DEVIATION_FEATURES = [
    "transaction_count",
    "failed_payment_rate",
    "retry_rate",
    "sku_diversity_ratio",
    "top_sku_share",
    "device_diversity_ratio",
    "ip_diversity_ratio",
    "new_customer_share",
    "repeat_customer_share",
    "amount_mean",
    "amount_cv",
]

# Thresholds for deviation significance
RELATIVE_DEVIATION_THRESHOLD = 0.20  # 20% change considered notable
STANDARDIZED_DEVIATION_THRESHOLD = 1.5  # 1.5 std devs considered notable


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class FeatureDeviation:
    """Structured deviation for a single feature."""
    feature_name: str
    current_value: float
    historical_baseline: Optional[float]
    absolute_difference: Optional[float]
    relative_difference: Optional[float]
    deviation_direction: str  # "higher", "lower", "stable"
    is_notable: bool
    standardized_deviation: Optional[float] = None


@dataclass
class ModelContribution:
    """Model contribution for a single feature."""
    feature_name: str
    coefficient: float
    feature_value: float
    contribution: float  # coefficient * feature_value (after scaling)
    is_positive: bool  # True if pushes toward fraud


@dataclass
class WindowExplanation:
    """Complete explanation for a single window."""
    merchant_id: str
    date: str
    anomaly_summary: str
    behavioral_deviations: list[FeatureDeviation]
    top_fraud_contributors: list[ModelContribution]
    top_organic_contributors: list[ModelContribution]
    confidence_summary: str
    explanation_text: str


# ---------------------------------------------------------------------------
# Feature Deviation Analysis
# ---------------------------------------------------------------------------


def analyze_feature_deviations(
    window_row: pd.Series,
    merchant_history: pd.DataFrame,
    features_to_analyze: list[str] = None,
) -> list[FeatureDeviation]:
    """
    Compare window features against merchant's historical baseline.

    Args:
        window_row: Single row from pipeline results with feature values
        merchant_history: DataFrame with historical features for this merchant
        features_to_analyze: List of feature names to compare

    Returns:
        List of FeatureDeviation objects
    """
    if features_to_analyze is None:
        features_to_analyze = DEVIATION_FEATURES

    deviations = []

    for feature in features_to_analyze:
        if feature not in window_row.index or feature not in merchant_history.columns:
            continue

        current_value = window_row[feature]

        # Calculate historical baseline
        historical_values = merchant_history[feature].values
        historical_baseline = np.mean(historical_values) if len(historical_values) > 0 else None

        # Calculate differences
        if historical_baseline is not None and historical_baseline != 0:
            absolute_diff = current_value - historical_baseline
            relative_diff = absolute_diff / abs(historical_baseline)

            # Standardized deviation if we have enough history
            historical_std = np.std(historical_values) if len(historical_values) > 1 else None
            if historical_std is not None and historical_std > 0:
                standardized = (current_value - historical_baseline) / historical_std
            else:
                standardized = None

            # Determine direction
            if abs(relative_diff) < 0.05:  # Within 5%
                direction = "stable"
            elif relative_diff > 0:
                direction = "higher"
            else:
                direction = "lower"

            # Determine if notable
            is_notable = (
                abs(relative_diff) > RELATIVE_DEVIATION_THRESHOLD or
                (standardized is not None and abs(standardized) > STANDARDIZED_DEVIATION_THRESHOLD)
            )
        else:
            absolute_diff = None
            relative_diff = None
            standardized = None
            direction = "unknown"
            is_notable = False

        deviations.append(FeatureDeviation(
            feature_name=feature,
            current_value=current_value,
            historical_baseline=historical_baseline,
            absolute_difference=absolute_diff,
            relative_difference=relative_diff,
            deviation_direction=direction,
            is_notable=is_notable,
            standardized_deviation=standardized,
        ))

    return deviations


# ---------------------------------------------------------------------------
# Model Contribution Analysis
# ---------------------------------------------------------------------------


def analyze_model_contributions(
    window_row: pd.Series,
    model: Pipeline,
    feature_cols: list[str],
    n_top: int = 5,
) -> tuple[list[ModelContribution], list[ModelContribution]]:
    """
    Derive feature contributions from the trained LogisticRegression model.

    The contribution is calculated as: coefficient * standardized_feature_value
    This accounts for the StandardScaler in the pipeline.

    Args:
        window_row: Single row with feature values
        model: Trained sklearn Pipeline with scaler and classifier
        feature_cols: Feature columns used by the model
        n_top: Number of top contributors to return

    Returns:
        Tuple of (top_fraud_contributors, top_organic_contributors)
    """
    # Extract coefficients from the pipeline
    clf = model.named_steps["classifier"]
    scaler = model.named_steps["scaler"]

    coefficients = clf.coef_[0]

    # Get feature values and standardize
    feature_values = np.array([window_row[col] for col in feature_cols])
    standardized_values = scaler.transform(feature_values.reshape(1, -1))[0]

    # Calculate contributions
    contributions = []
    for i, (col, coef, val, std_val) in enumerate(zip(feature_cols, coefficients, feature_values, standardized_values)):
        contribution = coef * std_val
        contributions.append(ModelContribution(
            feature_name=col,
            coefficient=coef,
            feature_value=val,
            contribution=contribution,
            is_positive=contribution > 0,  # Positive contribution pushes toward fraud
        ))

    # Sort by contribution magnitude
    fraud_contributors = sorted(contributions, key=lambda x: x.contribution, reverse=True)
    organic_contributors = sorted(contributions, key=lambda x: x.contribution)

    return fraud_contributors[:n_top], organic_contributors[:n_top]


# ---------------------------------------------------------------------------
# Anomaly Summary Generation
# ---------------------------------------------------------------------------


def generate_anomaly_summary(
    window_row: pd.Series,
    deviations: list[FeatureDeviation],
) -> str:
    """
    Generate a concise anomaly summary from deviations.

    Only includes notable deviations.
    """
    notable_deviations = [d for d in deviations if d.is_notable]

    if not notable_deviations:
        return "Minor anomaly detected, but no major behavioral deviations."

    # Find the most significant deviations
    summary_parts = []

    # Look for volume anomaly
    volume_dev = next((d for d in notable_deviations if d.feature_name == "transaction_count"), None)
    if volume_dev and volume_dev.relative_difference is not None:
        multiplier = 1 + volume_dev.relative_difference
        summary_parts.append(f"Transaction volume is {multiplier:.1f}x the merchant's baseline")

    # Look for payment behavior anomalies
    payment_dev = next((d for d in notable_deviations if d.feature_name == "failed_payment_rate"), None)
    if payment_dev and payment_dev.relative_difference is not None:
        if payment_dev.deviation_direction == "higher":
            summary_parts.append(f"Failed payment rate elevated by {abs(payment_dev.relative_difference)*100:.0f}%")
        else:
            summary_parts.append(f"Failed payment rate decreased by {abs(payment_dev.relative_difference)*100:.0f}%")

    # Look for device/IP concentration
    device_dev = next((d for d in notable_deviations if d.feature_name == "device_diversity_ratio"), None)
    if device_dev and device_dev.deviation_direction == "lower":
        summary_parts.append("Device diversity reduced (more concentrated)")

    ip_dev = next((d for d in notable_deviations if d.feature_name == "ip_diversity_ratio"), None)
    if ip_dev and ip_dev.deviation_direction == "lower":
        summary_parts.append("IP diversity reduced (more concentrated)")

    # Look for customer behavior
    new_cust_dev = next((d for d in notable_deviations if d.feature_name == "new_customer_share"), None)
    if new_cust_dev and new_cust_dev.deviation_direction == "higher":
        summary_parts.append("Unusually high proportion of new customers")

    repeat_cust_dev = next((d for d in notable_deviations if d.feature_name == "repeat_customer_share"), None)
    if repeat_cust_dev and repeat_cust_dev.deviation_direction == "lower":
        summary_parts.append("Lower-than-normal repeat customer activity")

    if not summary_parts:
        return f"Anomaly detected with {len(notable_deviations)} notable feature deviations."

    return "; ".join(summary_parts) + "."


# ---------------------------------------------------------------------------
# Explanation Text Generation
# ---------------------------------------------------------------------------


def generate_explanation_text(
    anomaly_summary: str,
    top_fraud_contributors: list[ModelContribution],
    confidence: float,
    predicted_cause: str,
) -> str:
    """
    Generate concise human-readable explanation from structured evidence.
    """
    # Start with anomaly summary
    text_parts = [anomaly_summary]

    # Add model contribution context
    if top_fraud_contributors:
        top_3 = top_fraud_contributors[:3]
        contributor_descriptions = []
        for c in top_3:
            direction = "elevated" if c.feature_value > 0 else "reduced"
            contributor_descriptions.append(f"{c.feature_name} ({direction})")
        text_parts.append(
            f"The {predicted_cause} classification was supported by: {', '.join(contributor_descriptions)}"
        )

    # Add confidence context
    text_parts.append(f"Model confidence was {confidence:.2f}")

    return ". ".join(text_parts) + "."


# ---------------------------------------------------------------------------
# Main Explanation Function
# ---------------------------------------------------------------------------


def explain_window(
    window_row: pd.Series,
    merchant_history: pd.DataFrame,
    model: Pipeline,
    feature_cols: list[str],
) -> WindowExplanation:
    """
    Generate a complete explanation for a single suspicious window.

    Args:
        window_row: Single row from pipeline results
        merchant_history: Historical features for this merchant
        model: Trained Stage 2 model
        feature_cols: Feature columns used by the model

    Returns:
        WindowExplanation object with structured explanation
    """
    # Feature deviation analysis
    deviations = analyze_feature_deviations(window_row, merchant_history, feature_cols)

    # Model contribution analysis
    top_fraud, top_organic = analyze_model_contributions(window_row, model, feature_cols)

    # Anomaly summary
    anomaly_summary = generate_anomaly_summary(window_row, deviations)

    # Confidence summary
    confidence = window_row.get("confidence", 0.0)
    confidence_band = window_row.get("confidence_band", "unknown")
    predicted_cause = window_row.get("predicted_cause", "unknown")

    confidence_summary = f"Confidence: {confidence:.2f} ({confidence_band})"

    # Generate explanation text
    explanation_text = generate_explanation_text(
        anomaly_summary, top_fraud, confidence, predicted_cause
    )

    return WindowExplanation(
        merchant_id=window_row["merchant_id"],
        date=str(window_row["date"]),
        anomaly_summary=anomaly_summary,
        behavioral_deviations=deviations,
        top_fraud_contributors=top_fraud,
        top_organic_contributors=top_organic,
        confidence_summary=confidence_summary,
        explanation_text=explanation_text,
    )


# ---------------------------------------------------------------------------
# Batch Explanation
# ---------------------------------------------------------------------------


def explain_windows_batch(
    pipeline_results: pd.DataFrame,
    window_features: pd.DataFrame,
    model: Pipeline,
    feature_cols: list[str],
) -> pd.DataFrame:
    """
    Generate explanations for all detected spikes in batch.

    Returns DataFrame with explanation fields added.
    """
    results = pipeline_results.copy()

    # Initialize explanation columns
    results["anomaly_summary"] = ""
    results["top_fraud_signal"] = ""
    results["top_organic_signal"] = ""
    results["explanation_text"] = ""

    # Process only detected spikes
    spike_mask = results["is_spike"] == True

    for idx in results[spike_mask].index:
        window_row = results.loc[idx]
        merchant = window_row["merchant_id"]

        # Get merchant history (excluding current window)
        merchant_history = window_features[
            (window_features["merchant_id"] == merchant) &
            (window_features["date"] != window_row["date"])
        ]

        # Skip if insufficient history
        if len(merchant_history) < 2:
            results.loc[idx, "anomaly_summary"] = "Insufficient historical data for comparison"
            results.loc[idx, "explanation_text"] = "Anomaly detected but limited historical context available"
            continue

        # Generate explanation
        explanation = explain_window(window_row, merchant_history, model, feature_cols)

        # Store results
        results.loc[idx, "anomaly_summary"] = explanation.anomaly_summary
        results.loc[idx, "explanation_text"] = explanation.explanation_text

        # Top signals
        if explanation.top_fraud_contributors:
            top = explanation.top_fraud_contributors[0]
            results.loc[idx, "top_fraud_signal"] = f"{top.feature_name} (coeff={top.coefficient:.3f})"
        if explanation.top_organic_contributors:
            top = explanation.top_organic_contributors[0]
            results.loc[idx, "top_organic_signal"] = f"{top.feature_name} (coeff={top.coefficient:.3f})"

    return results
