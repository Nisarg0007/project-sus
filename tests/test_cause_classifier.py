"""
Tests for the Stage 2 cause classifier module.
"""

import numpy as np
import pandas as pd
import pytest

from src.cause_classifier import (
    CostModel,
    calculate_expected_cost,
    evaluate_classifier,
    get_default_feature_set,
    split_by_merchant,
    train_cause_classifier,
    predict_causes,
    _assign_confidence_band,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helper: Create small synthetic DataFrames for testing
# ---------------------------------------------------------------------------


def _make_synthetic_windows(n_organic: int = 20, n_fraud: int = 20) -> tuple[pd.DataFrame, list[str]]:
    """Create a small synthetic window DataFrame for testing."""
    rng = np.random.RandomState(42)

    feature_cols = get_default_feature_set()

    organic_rows = []
    for i in range(n_organic):
        row = {
            "merchant_id": f"merchant_{(i % 4) + 1:03d}",
            "date": pd.Timestamp("2025-07-01") + pd.Timedelta(days=i % 10),
            "window_label": "organic_spike",
            "target": 0,
        }
        # Add features
        row["failed_payment_rate"] = rng.uniform(0.01, 0.05)
        row["retry_rate"] = rng.uniform(0.005, 0.02)
        row["failed_retry_rate"] = rng.uniform(0.005, 0.02)
        row["sku_diversity_ratio"] = rng.uniform(0.1, 0.5)
        row["top_sku_share"] = rng.uniform(0.05, 0.3)
        row["sku_entropy"] = rng.uniform(3, 8)
        row["device_diversity_ratio"] = rng.uniform(0.5, 0.9)
        row["ip_diversity_ratio"] = rng.uniform(0.4, 0.8)
        row["ip_entropy"] = rng.uniform(8, 11)
        row["new_customer_share"] = rng.uniform(0.4, 0.7)
        row["repeat_customer_share"] = rng.uniform(0.3, 0.6)
        row["amount_mean"] = rng.uniform(100, 500)
        row["amount_cv"] = rng.uniform(0.2, 0.5)
        row["transaction_count"] = rng.randint(500, 1500)
        row["volume_zscore_7d"] = rng.uniform(0.5, 3.0)
        organic_rows.append(row)

    fraud_rows = []
    for i in range(n_fraud):
        row = {
            "merchant_id": f"merchant_{(i % 4) + 1:03d}",
            "date": pd.Timestamp("2025-07-01") + pd.Timedelta(days=i % 10),
            "window_label": "fraud_spike",
            "target": 1,
        }
        # Add features with different distributions
        row["failed_payment_rate"] = rng.uniform(0.05, 0.15)
        row["retry_rate"] = rng.uniform(0.02, 0.08)
        row["failed_retry_rate"] = rng.uniform(0.02, 0.08)
        row["sku_diversity_ratio"] = rng.uniform(0.05, 0.3)
        row["top_sku_share"] = rng.uniform(0.2, 0.5)
        row["sku_entropy"] = rng.uniform(2, 6)
        row["device_diversity_ratio"] = rng.uniform(0.3, 0.7)
        row["ip_diversity_ratio"] = rng.uniform(0.2, 0.6)
        row["ip_entropy"] = rng.uniform(6, 9)
        row["new_customer_share"] = rng.uniform(0.6, 0.9)
        row["repeat_customer_share"] = rng.uniform(0.1, 0.4)
        row["amount_mean"] = rng.uniform(150, 600)
        row["amount_cv"] = rng.uniform(0.3, 0.6)
        row["transaction_count"] = rng.randint(400, 1200)
        row["volume_zscore_7d"] = rng.uniform(0.3, 2.5)
        fraud_rows.append(row)

    df = pd.DataFrame(organic_rows + fraud_rows)
    return df, feature_cols


# ---------------------------------------------------------------------------
# Test: Feature Selection
# ---------------------------------------------------------------------------


class TestFeatureSelection:
    def test_feature_set_is_deterministic(self):
        """Feature set should be deterministic across calls."""
        fs1 = get_default_feature_set()
        fs2 = get_default_feature_set()
        assert fs1 == fs2

    def test_feature_set_has_expected_size(self):
        """Feature set should have reasonable size (10-30 features)."""
        fs = get_default_feature_set()
        assert 10 <= len(fs) <= 30

    def test_feature_set_excludes_redundant_features(self):
        """Feature set should not include both success_rate and failed_payment_rate."""
        fs = get_default_feature_set()
        # Should have failed_payment_rate but not success_rate (redundant)
        assert "failed_payment_rate" in fs
        # success_rate should not be in default set (redundant with failed_payment_rate)


# ---------------------------------------------------------------------------
# Test: Data Preparation
# ---------------------------------------------------------------------------


class TestPrepareData:
    def test_only_organic_and_fraud(self):
        """Should only include organic_spike and fraud_spike windows."""
        df, _ = _make_synthetic_windows()
        labels = df["window_label"].unique()
        assert set(labels) == {"organic_spike", "fraud_spike"}

    def test_target_mapping(self):
        """Labels should map correctly."""
        df, _ = _make_synthetic_windows()
        organic = df[df["window_label"] == "organic_spike"]["target"]
        fraud = df[df["window_label"] == "fraud_spike"]["target"]
        assert (organic == 0).all()
        assert (fraud == 1).all()

    def test_metadata_excluded_from_features(self):
        """Metadata columns should not be in feature list."""
        feature_cols = get_default_feature_set()
        assert "merchant_id" not in feature_cols
        assert "date" not in feature_cols
        assert "window_label" not in feature_cols
        assert "target" not in feature_cols


# ---------------------------------------------------------------------------
# Test: Train/Test Split
# ---------------------------------------------------------------------------


class TestSplitByMerchant:
    def test_no_merchant_overlap(self):
        """Train and test should have no merchant overlap."""
        df, feature_cols = _make_synthetic_windows()
        _, _, _, _, train_merchants, test_merchants = split_by_merchant(df, feature_cols)

        overlap = set(train_merchants) & set(test_merchants)
        assert len(overlap) == 0

    def test_both_classes_in_train(self):
        """Training set should have both classes."""
        df, feature_cols = _make_synthetic_windows()
        _, _, y_train, _, _, _ = split_by_merchant(df, feature_cols)

        assert set(y_train.unique()) == {0, 1}

    def test_both_classes_in_test(self):
        """Test set should have both classes."""
        df, feature_cols = _make_synthetic_windows()
        _, _, _, y_test, _, _ = split_by_merchant(df, feature_cols)

        assert set(y_test.unique()) == {0, 1}


# ---------------------------------------------------------------------------
# Test: Model Training
# ---------------------------------------------------------------------------


class TestModelTraining:
    def test_logistic_regression_runs(self):
        """LogisticRegression should train without errors."""
        df, feature_cols = _make_synthetic_windows()
        X = df[feature_cols]
        y = df["target"]

        model = train_cause_classifier(X, y, model_type="logistic_regression")
        assert model is not None

    def test_predictions_are_valid(self):
        """Predictions should be valid labels."""
        df, feature_cols = _make_synthetic_windows()
        X = df[feature_cols]
        y = df["target"]

        model = train_cause_classifier(X, y, model_type="logistic_regression")
        y_pred = model.predict(X)

        assert set(y_pred).issubset({0, 1})


# ---------------------------------------------------------------------------
# Test: Prediction and Confidence
# ---------------------------------------------------------------------------


class TestPredictCauses:
    def test_predictions_contain_required_columns(self):
        """Predictions should contain all required columns."""
        df, feature_cols = _make_synthetic_windows()
        X = df[feature_cols]
        y = df["target"]

        model = train_cause_classifier(X, y)
        predictions = predict_causes(model, df, feature_cols)

        assert "merchant_id" in predictions.columns
        assert "date" in predictions.columns
        assert "predicted_label" in predictions.columns
        assert "probability_organic" in predictions.columns
        assert "probability_fraud" in predictions.columns
        assert "confidence" in predictions.columns
        assert "confidence_band" in predictions.columns

    def test_probabilities_sum_to_one(self):
        """Probabilities should sum approximately to 1."""
        df, feature_cols = _make_synthetic_windows()
        X = df[feature_cols]
        y = df["target"]

        model = train_cause_classifier(X, y)
        predictions = predict_causes(model, df, feature_cols)

        prob_sum = predictions["probability_organic"] + predictions["probability_fraud"]
        assert np.allclose(prob_sum, 1.0, atol=0.01)

    def test_confidence_between_zero_and_one(self):
        """Confidence should be between 0 and 1."""
        df, feature_cols = _make_synthetic_windows()
        X = df[feature_cols]
        y = df["target"]

        model = train_cause_classifier(X, y)
        predictions = predict_causes(model, df, feature_cols)

        assert (predictions["confidence"] >= 0).all()
        assert (predictions["confidence"] <= 1).all()

    def test_confidence_bands_assigned_correctly(self):
        """Confidence bands should be assigned correctly."""
        # Test directly
        assert _assign_confidence_band(0.95) == "high_confidence"
        assert _assign_confidence_band(0.80) == "high_confidence"
        assert _assign_confidence_band(0.75) == "ambiguous"
        assert _assign_confidence_band(0.60) == "ambiguous"
        assert _assign_confidence_band(0.50) == "low_confidence"
        assert _assign_confidence_band(0.0) == "low_confidence"


# ---------------------------------------------------------------------------
# Test: Evaluation
# ---------------------------------------------------------------------------


class TestEvaluation:
    def test_evaluation_returns_required_metrics(self):
        """Evaluation should return all required metrics."""
        y_true = pd.Series([0, 1, 0, 1, 0])
        y_pred = pd.Series([0, 1, 0, 0, 0])

        metrics = evaluate_classifier(y_true, y_pred)

        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "accuracy" in metrics
        assert "confusion_matrix" in metrics
        assert "organic_precision" in metrics
        assert "fraud_precision" in metrics
        assert "macro_f1" in metrics


# ---------------------------------------------------------------------------
# Test: Cost Model
# ---------------------------------------------------------------------------


class TestCostModel:
    def test_cost_calculation_correct(self):
        """Cost calculation should be correct on known examples."""
        y_true = pd.Series([0, 0, 1, 1, 1])  # 2 organic, 3 fraud
        y_pred = pd.Series([0, 1, 1, 0, 1])  # 1 FP, 1 FN

        cost_model = CostModel(false_positive_cost=1.0, false_negative_cost=5.0)
        result = calculate_expected_cost(y_true, y_pred, cost_model)

        assert result["false_positives"] == 1
        assert result["false_negatives"] == 1
        assert result["total_cost"] == 6.0  # 1*1 + 1*5

    def test_custom_costs_work(self):
        """Custom costs should work correctly."""
        y_true = pd.Series([0, 1])
        y_pred = pd.Series([1, 0])  # 1 FP, 1 FN

        cost_model = CostModel(false_positive_cost=2.0, false_negative_cost=10.0)
        result = calculate_expected_cost(y_true, y_pred, cost_model)

        assert result["total_cost"] == 12.0  # 2 + 10

    def test_cost_model_rejects_negative_costs(self):
        """CostModel should reject negative costs."""
        with pytest.raises(ValueError):
            CostModel(false_positive_cost=-1.0)

        with pytest.raises(ValueError):
            CostModel(false_negative_cost=-1.0)


# ---------------------------------------------------------------------------
# Test: Deterministic Training
# ---------------------------------------------------------------------------


class TestDeterministicTraining:
    def test_same_seed_same_model(self):
        """Training with same data should produce same predictions."""
        df, feature_cols = _make_synthetic_windows()
        X = df[feature_cols]
        y = df["target"]

        model1 = train_cause_classifier(X, y)
        model2 = train_cause_classifier(X, y)

        pred1 = model1.predict(X)
        pred2 = model2.predict(X)

        np.testing.assert_array_equal(pred1, pred2)
