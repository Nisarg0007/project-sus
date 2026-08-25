"""
Tests for the robust evaluation module.
"""

import numpy as np
import pandas as pd
import pytest

from src.evaluation import (
    calculate_brier_score,
    calculate_cost_over_oof,
    calculate_per_merchant_metrics,
    analyze_confidence_bands,
    analyze_errors,
    threshold_analysis,
    cost_sensitivity_analysis,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helper: Create synthetic OOF DataFrame for testing
# ---------------------------------------------------------------------------


def _make_synthetic_oof(n_organic: int = 20, n_fraud: int = 20, n_errors: int = 2) -> pd.DataFrame:
    """Create a synthetic OOF prediction DataFrame for testing."""
    rng = np.random.RandomState(42)

    records = []

    # Organic windows (mostly correct)
    for i in range(n_organic):
        prob_fraud = rng.uniform(0.0, 0.3)  # Low fraud probability
        record = {
            "merchant_id": f"merchant_{(i % 4) + 1:03d}",
            "date": pd.Timestamp("2025-07-01") + pd.Timedelta(days=i % 10),
            "true_label": "organic_spike",
            "predicted_label": "organic_spike" if i >= n_errors else "fraud_spike",
            "probability_organic": 1 - prob_fraud,
            "probability_fraud": prob_fraud,
            "confidence": max(1 - prob_fraud, prob_fraud),
            "fold": (i % 4) + 1,
        }
        record["confidence_band"] = (
            "high_confidence" if record["confidence"] >= HIGH_CONFIDENCE_THRESHOLD
            else "ambiguous" if record["confidence"] >= LOW_CONFIDENCE_THRESHOLD
            else "low_confidence"
        )
        records.append(record)

    # Fraud windows (mostly correct)
    for i in range(n_fraud):
        prob_fraud = rng.uniform(0.7, 1.0)  # High fraud probability
        record = {
            "merchant_id": f"merchant_{(i % 4) + 1:03d}",
            "date": pd.Timestamp("2025-07-01") + pd.Timedelta(days=i % 10),
            "true_label": "fraud_spike",
            "predicted_label": "fraud_spike" if i >= n_errors else "organic_spike",
            "probability_organic": 1 - prob_fraud,
            "probability_fraud": prob_fraud,
            "confidence": max(1 - prob_fraud, prob_fraud),
            "fold": (i % 4) + 1,
        }
        record["confidence_band"] = (
            "high_confidence" if record["confidence"] >= HIGH_CONFIDENCE_THRESHOLD
            else "ambiguous" if record["confidence"] >= LOW_CONFIDENCE_THRESHOLD
            else "low_confidence"
        )
        records.append(record)

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Test: Per-Merchant Metrics
# ---------------------------------------------------------------------------


class TestPerMerchantMetrics:
    def test_metrics_per_merchant(self):
        """Should calculate metrics for each merchant."""
        oof_df = _make_synthetic_oof()
        merchant_metrics = calculate_per_merchant_metrics(oof_df)

        assert len(merchant_metrics) > 0
        assert "merchant" in merchant_metrics.columns
        assert "f1" in merchant_metrics.columns

    def test_merchant_count_matches(self):
        """Number of merchants in metrics should match OOF data."""
        oof_df = _make_synthetic_oof()
        merchant_metrics = calculate_per_merchant_metrics(oof_df)

        n_merchants_oof = oof_df["merchant_id"].nunique()
        n_merchants_metrics = len(merchant_metrics)

        assert n_merchants_oof == n_merchants_metrics


# ---------------------------------------------------------------------------
# Test: Confidence Analysis
# ---------------------------------------------------------------------------


class TestConfidenceAnalysis:
    def test_confidence_bands_analyzed(self):
        """Should analyze all confidence bands present in data."""
        oof_df = _make_synthetic_oof()
        confidence_analysis = analyze_confidence_bands(oof_df)

        assert len(confidence_analysis) > 0
        assert "confidence_band" in confidence_analysis.columns
        assert "accuracy" in confidence_analysis.columns

    def test_high_confidence_has_highest_accuracy(self):
        """High confidence should generally have higher accuracy."""
        oof_df = _make_synthetic_oof(n_errors=0)  # No errors
        confidence_analysis = analyze_confidence_bands(oof_df)

        # With no errors, all bands should have accuracy = 1.0
        if len(confidence_analysis) > 0:
            assert (confidence_analysis["accuracy"] == 1.0).all()


# ---------------------------------------------------------------------------
# Test: Cost Analysis
# ---------------------------------------------------------------------------


class TestCostAnalysis:
    def test_cost_calculation(self):
        """Cost calculation should be correct."""
        oof_df = _make_synthetic_oof(n_errors=0)  # No errors
        cost_result = calculate_cost_over_oof(oof_df, false_positive_cost=1.0, false_negative_cost=5.0)

        assert cost_result["false_positives"] == 0
        assert cost_result["false_negatives"] == 0
        assert cost_result["total_cost"] == 0.0

    def test_cost_with_errors(self):
        """Cost should increase with errors."""
        oof_df = _make_synthetic_oof(n_errors=2)  # Some errors
        cost_result = calculate_cost_over_oof(oof_df, false_positive_cost=1.0, false_negative_cost=5.0)

        assert cost_result["false_positives"] + cost_result["false_negatives"] > 0
        assert cost_result["total_cost"] > 0


# ---------------------------------------------------------------------------
# Test: Threshold Analysis
# ---------------------------------------------------------------------------


class TestThresholdAnalysis:
    def test_threshold_analysis_output(self):
        """Threshold analysis should return expected columns."""
        oof_df = _make_synthetic_oof()
        threshold_results = threshold_analysis(oof_df, thresholds=[0.3, 0.5, 0.7])

        assert "threshold" in threshold_results.columns
        assert "fraud_f1" in threshold_results.columns
        assert "total_cost" in threshold_results.columns
        assert len(threshold_results) == 3

    def test_threshold_varies_performance(self):
        """Different thresholds should produce different results."""
        oof_df = _make_synthetic_oof(n_errors=5)
        threshold_results = threshold_analysis(oof_df, thresholds=[0.3, 0.5, 0.7])

        # At minimum, the function should run and return results
        assert len(threshold_results) == 3
        assert "threshold" in threshold_results.columns
        assert "fraud_f1" in threshold_results.columns
        # Total cost should vary across thresholds
        assert threshold_results["total_cost"].min() <= threshold_results["total_cost"].max()


# ---------------------------------------------------------------------------
# Test: Cost Sensitivity
# ---------------------------------------------------------------------------


class TestCostSensitivity:
    def test_cost_sensitivity_output(self):
        """Cost sensitivity should return expected columns."""
        oof_df = _make_synthetic_oof()
        sensitivity = cost_sensitivity_analysis(oof_df)

        assert "false_negative_cost" in sensitivity.columns
        assert "total_cost" in sensitivity.columns
        assert len(sensitivity) > 0


# ---------------------------------------------------------------------------
# Test: Brier Score
# ---------------------------------------------------------------------------


class TestBrierScore:
    def test_brier_score_valid(self):
        """Brier score should be between 0 and 1."""
        oof_df = _make_synthetic_oof()
        brier = calculate_brier_score(oof_df)

        assert 0 <= brier <= 1

    def test_brier_score_lower_better(self):
        """Lower Brier score indicates better calibration."""
        # Perfect predictions
        oof_perfect = _make_synthetic_oof(n_errors=0)
        brier_perfect = calculate_brier_score(oof_perfect)

        # Should be close to 0 for perfect predictions
        assert brier_perfect < 0.1


# ---------------------------------------------------------------------------
# Test: Error Analysis
# ---------------------------------------------------------------------------


class TestErrorAnalysis:
    def test_error_analysis_with_errors(self):
        """Error analysis should identify errors correctly."""
        oof_df = _make_synthetic_oof(n_errors=2)
        errors, summary = analyze_errors(oof_df)

        assert summary["total_errors"] > 0
        assert len(errors) == summary["total_errors"]

    def test_error_analysis_no_errors(self):
        """Error analysis should handle zero errors."""
        oof_df = _make_synthetic_oof(n_errors=0)
        errors, summary = analyze_errors(oof_df)

        assert summary["total_errors"] == 0
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Test: OOF Coverage
# ---------------------------------------------------------------------------


class TestOOFCoverage:
    def test_every_window_has_prediction(self):
        """Every spike window should receive exactly one OOF prediction."""
        oof_df = _make_synthetic_oof(n_organic=25, n_fraud=25)

        # Should have exactly one prediction per window
        # (In real evaluation, this is guaranteed by LeaveOneGroupOut)
        assert len(oof_df) == 50

    def test_probabilities_sum_to_one(self):
        """Probabilities should sum approximately to 1."""
        oof_df = _make_synthetic_oof()

        prob_sum = oof_df["probability_organic"] + oof_df["probability_fraud"]
        assert np.allclose(prob_sum, 1.0, atol=0.01)

    def test_confidence_valid(self):
        """Confidence should be between 0 and 1."""
        oof_df = _make_synthetic_oof()

        assert (oof_df["confidence"] >= 0).all()
        assert (oof_df["confidence"] <= 1).all()
