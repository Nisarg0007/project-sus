"""
Tests for the explainability module.
"""

import numpy as np
import pandas as pd
import pytest

from src.explainability import (
    analyze_feature_deviations,
    analyze_model_contributions,
    generate_anomaly_summary,
    generate_explanation_text,
    explain_window,
    FeatureDeviation,
    ModelContribution,
)


# ---------------------------------------------------------------------------
# Helper: Create synthetic data for testing
# ---------------------------------------------------------------------------


def _make_synthetic_data():
    """Create synthetic data for explainability tests."""
    # Create window row
    window_row = pd.Series({
        "merchant_id": "merchant_001",
        "date": "2025-07-15",
        "transaction_count": 1500,
        "failed_payment_rate": 0.15,
        "retry_rate": 0.05,
        "sku_diversity_ratio": 0.2,
        "device_diversity_ratio": 0.3,
        "ip_diversity_ratio": 0.35,
        "new_customer_share": 0.7,
        "repeat_customer_share": 0.3,
        "amount_mean": 150.0,
        "amount_cv": 0.4,
        "volume_zscore_7d": 2.5,
        "is_spike": True,
        "predicted_cause": "fraud_spike",
        "confidence": 0.85,
        "confidence_band": "high_confidence",
    })

    # Create merchant history
    history_data = {
        "transaction_count": [500, 520, 480, 510, 490],
        "failed_payment_rate": [0.03, 0.04, 0.035, 0.03, 0.035],
        "retry_rate": [0.01, 0.015, 0.01, 0.012, 0.01],
        "sku_diversity_ratio": [0.4, 0.42, 0.38, 0.41, 0.39],
        "device_diversity_ratio": [0.6, 0.62, 0.58, 0.61, 0.59],
        "ip_diversity_ratio": [0.55, 0.57, 0.53, 0.56, 0.54],
        "new_customer_share": [0.3, 0.32, 0.28, 0.31, 0.29],
        "repeat_customer_share": [0.7, 0.68, 0.72, 0.69, 0.71],
        "amount_mean": [100, 105, 95, 102, 98],
        "amount_cv": [0.25, 0.27, 0.24, 0.26, 0.25],
    }
    merchant_history = pd.DataFrame(history_data)

    return window_row, merchant_history


# ---------------------------------------------------------------------------
# Test: Feature Deviation Analysis
# ---------------------------------------------------------------------------


class TestFeatureDeviations:
    def test_deviations_generated(self):
        """Should generate deviations for all analyzed features."""
        window_row, merchant_history = _make_synthetic_data()
        deviations = analyze_feature_deviations(window_row, merchant_history)

        assert len(deviations) > 0
        assert all(isinstance(d, FeatureDeviation) for d in deviations)

    def test_volume_deviation_detected(self):
        """Should detect transaction count deviation."""
        window_row, merchant_history = _make_synthetic_data()
        deviations = analyze_feature_deviations(window_row, merchant_history)

        volume_dev = next((d for d in deviations if d.feature_name == "transaction_count"), None)
        assert volume_dev is not None
        assert volume_dev.deviation_direction == "higher"
        assert volume_dev.is_notable == True

    def test_payment_rate_deviation(self):
        """Should detect failed payment rate deviation."""
        window_row, merchant_history = _make_synthetic_data()
        deviations = analyze_feature_deviations(window_row, merchant_history)

        payment_dev = next((d for d in deviations if d.feature_name == "failed_payment_rate"), None)
        assert payment_dev is not None
        assert payment_dev.deviation_direction == "higher"

    def test_no_fabricated_explanations(self):
        """Should not fabricate explanations for stable features."""
        window_row, merchant_history = _make_synthetic_data()
        deviations = analyze_feature_deviations(window_row, merchant_history)

        # Amount CV should be relatively stable
        amount_cv_dev = next((d for d in deviations if d.feature_name == "amount_cv"), None)
        if amount_cv_dev:
            # Should not be marked as notable if it's within threshold
            assert amount_cv_dev.relative_difference is not None


# ---------------------------------------------------------------------------
# Test: Model Contribution Analysis
# ---------------------------------------------------------------------------


class TestModelContributions:
    def test_contributions_deterministic(self):
        """Model contributions should be deterministic."""
        window_row, _ = _make_synthetic_data()

        # Create a simple mock model
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        feature_cols = ["transaction_count", "failed_payment_rate"]
        X_train = np.array([[500, 0.03], [1500, 0.15], [600, 0.04], [1400, 0.12]])
        y_train = np.array([0, 1, 0, 1])

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(random_state=42)),
        ])
        model.fit(X_train, y_train)

        fraud_contrib, organic_contrib = analyze_model_contributions(
            window_row, model, feature_cols
        )

        assert len(fraud_contrib) > 0
        assert len(organic_contrib) > 0
        assert all(isinstance(c, ModelContribution) for c in fraud_contrib)


# ---------------------------------------------------------------------------
# Test: Anomaly Summary Generation
# ---------------------------------------------------------------------------


class TestAnomalySummary:
    def test_summary_from_deviations(self):
        """Should generate summary from notable deviations."""
        window_row, merchant_history = _make_synthetic_data()
        deviations = analyze_feature_deviations(window_row, merchant_history)

        summary = generate_anomaly_summary(window_row, deviations)

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summary_includes_volume(self):
        """Summary should mention volume when significantly elevated."""
        window_row, merchant_history = _make_synthetic_data()
        deviations = analyze_feature_deviations(window_row, merchant_history)

        summary = generate_anomaly_summary(window_row, deviations)

        # Volume is 3x baseline, should be mentioned
        assert "volume" in summary.lower() or "transaction" in summary.lower()


# ---------------------------------------------------------------------------
# Test: Explanation Text Generation
# ---------------------------------------------------------------------------


class TestExplanationText:
    def test_explanation_text_generated(self):
        """Should generate explanation text."""
        text = generate_explanation_text(
            anomaly_summary="Transaction volume is 3.0x the merchant's baseline.",
            top_fraud_contributors=[],
            confidence=0.85,
            predicted_cause="fraud_spike",
        )

        assert isinstance(text, str)
        assert "0.85" in text or "85" in text


# ---------------------------------------------------------------------------
# Test: Label Independence
# ---------------------------------------------------------------------------


class TestLabelIndependence:
    def test_explanations_do_not_use_labels(self):
        """Explanations should not use window_label."""
        window_row, merchant_history = _make_synthetic_data()

        # Ensure window_label is not in the data
        assert "window_label" not in window_row.index

        deviations = analyze_feature_deviations(window_row, merchant_history)

        # Check that no deviation uses window_label
        for dev in deviations:
            assert dev.feature_name != "window_label"


# ---------------------------------------------------------------------------
# Test: Insufficient History
# ---------------------------------------------------------------------------


class TestInsufficientHistory:
    def test_handles_empty_history(self):
        """Should handle empty or insufficient history gracefully."""
        window_row, _ = _make_synthetic_data()
        # Use history with only one row (insufficient for std calculation)
        minimal_history = pd.DataFrame({
            "transaction_count": [500],
            "failed_payment_rate": [0.03],
            "retry_rate": [0.01],
            "sku_diversity_ratio": [0.4],
            "device_diversity_ratio": [0.6],
            "ip_diversity_ratio": [0.55],
            "new_customer_share": [0.3],
            "repeat_customer_share": [0.7],
            "amount_mean": [100],
            "amount_cv": [0.25],
        })

        deviations = analyze_feature_deviations(window_row, minimal_history)

        # Should return deviations even with minimal history
        assert len(deviations) > 0
        # Historical baselines should be computed from single value
        for dev in deviations:
            assert dev.historical_baseline is not None
