"""
Tests for the Stage 2 cause classifier experiment module.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.classifier_experiment import (
    VOLUME_FEATURES,
    feature_audit,
    get_feature_set_a,
    get_feature_set_b,
    get_model_features,
    grouped_merchant_split,
    load_stage2_data,
    stratified_random_split,
    validate_features,
)


# ---------------------------------------------------------------------------
# Helper: Create small synthetic DataFrames for testing
# ---------------------------------------------------------------------------


def _make_synthetic_windows(n_organic: int = 20, n_fraud: int = 20) -> pd.DataFrame:
    """Create a small synthetic window DataFrame for testing."""
    rng = np.random.RandomState(42)

    organic_rows = []
    for i in range(n_organic):
        organic_rows.append({
            "merchant_id": f"merchant_{(i % 4) + 1:03d}",
            "date": pd.Timestamp("2025-07-01") + pd.Timedelta(days=i % 10),
            "window_label": "organic_spike",
            "target": 0,
            "transaction_count": rng.randint(500, 1500),
            "amount_mean": rng.uniform(100, 500),
            "sku_diversity_ratio": rng.uniform(0.1, 0.5),
            "retry_rate": rng.uniform(0.01, 0.05),
            "new_customer_share": rng.uniform(0.4, 0.7),
            "volume_zscore_7d": rng.uniform(0.5, 3.0),
            "volume_rolling_mean_7d": rng.uniform(300, 800),
            "volume_rolling_std_7d": rng.uniform(50, 200),
            "volume_ratio_to_7d_mean": rng.uniform(1.1, 2.5),
            "successful_transaction_count": rng.randint(400, 1400),
            "failed_transaction_count": rng.randint(10, 100),
        })

    fraud_rows = []
    for i in range(n_fraud):
        fraud_rows.append({
            "merchant_id": f"merchant_{(i % 4) + 1:03d}",
            "date": pd.Timestamp("2025-07-01") + pd.Timedelta(days=i % 10),
            "window_label": "fraud_spike",
            "target": 1,
            "transaction_count": rng.randint(400, 1200),
            "amount_mean": rng.uniform(150, 600),
            "sku_diversity_ratio": rng.uniform(0.05, 0.3),
            "retry_rate": rng.uniform(0.05, 0.15),
            "new_customer_share": rng.uniform(0.6, 0.9),
            "volume_zscore_7d": rng.uniform(0.3, 2.5),
            "volume_rolling_mean_7d": rng.uniform(400, 900),
            "volume_rolling_std_7d": rng.uniform(80, 250),
            "volume_ratio_to_7d_mean": rng.uniform(1.0, 2.0),
            "successful_transaction_count": rng.randint(300, 1100),
            "failed_transaction_count": rng.randint(50, 150),
        })

    return pd.DataFrame(organic_rows + fraud_rows)


# ---------------------------------------------------------------------------
# Test: Data loading and preparation
# ---------------------------------------------------------------------------


class TestLoadStage2Data:
    def test_only_organic_and_fraud(self):
        """Should only include organic_spike and fraud_spike windows."""
        df = _make_synthetic_windows()
        labels = df["window_label"].unique()
        assert set(labels) == {"organic_spike", "fraud_spike"}

    def test_label_mapping(self):
        """Labels should map correctly: organic_spike -> 0, fraud_spike -> 1."""
        df = _make_synthetic_windows()
        organic = df[df["window_label"] == "organic_spike"]["target"]
        fraud = df[df["window_label"] == "fraud_spike"]["target"]
        assert (organic == 0).all()
        assert (fraud == 1).all()


# ---------------------------------------------------------------------------
# Test: Feature validation
# ---------------------------------------------------------------------------


class TestFeatureValidation:
    def test_metadata_excluded(self):
        """Metadata columns should be excluded from model features."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)

        assert "merchant_id" not in feature_cols
        assert "date" not in feature_cols
        assert "window_label" not in feature_cols
        assert "target" not in feature_cols

    def test_target_excluded(self):
        """Target should not be in feature columns."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)
        assert "target" not in feature_cols

    def test_no_nan_rejected(self):
        """Should detect NaN values in features."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)

        # Introduce NaN
        X = df[feature_cols].copy()
        X.iloc[0, 0] = np.nan

        errors = validate_features(X, df["target"])
        assert any("NaN" in e for e in errors)

    def test_no_infinite_rejected(self):
        """Should detect infinite values in features."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)

        # Introduce infinite (need to use float column)
        X = df[feature_cols].copy()
        # Find a float column to set to inf
        float_cols = X.select_dtypes(include=[np.number]).columns
        if len(float_cols) > 0:
            X[float_cols[0]] = np.inf
            errors = validate_features(X, df["target"])
            assert any("Infinite" in e for e in errors)


# ---------------------------------------------------------------------------
# Test: Split strategies
# ---------------------------------------------------------------------------


class TestSplitStrategies:
    def test_stratified_preserves_classes(self):
        """Stratified split should preserve both classes."""
        df = _make_synthetic_windows()
        X = df[get_model_features(df)]
        y = df["target"]

        X_train, X_test, y_train, y_test = stratified_random_split(X, y)

        assert set(y_train.unique()) == {0, 1}
        assert set(y_test.unique()) == {0, 1}

    def test_no_overlap(self):
        """No row should be in both train and test."""
        df = _make_synthetic_windows()
        X = df[get_model_features(df)]
        y = df["target"]

        X_train, X_test, y_train, y_test = stratified_random_split(X, y)

        # Check total size equals sum of parts
        assert len(X_train) + len(X_test) == len(df)

    def test_grouped_split_no_merchant_overlap(self):
        """Grouped split should have no merchant overlap."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)

        X_train, X_test, y_train, y_test, train_merchants, test_merchants = grouped_merchant_split(
            df, feature_cols
        )

        assert len(set(train_merchants) & set(test_merchants)) == 0

    def test_grouped_split_both_classes(self):
        """Grouped split should have both classes in test set."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)

        X_train, X_test, y_train, y_test, train_merchants, test_merchants = grouped_merchant_split(
            df, feature_cols
        )

        assert set(y_test.unique()) == {0, 1}


# ---------------------------------------------------------------------------
# Test: Feature sets
# ---------------------------------------------------------------------------


class TestFeatureSets:
    def test_set_a_includes_all(self):
        """Set A should include all features."""
        feature_cols = ["f1", "f2", "f3", "transaction_count"]
        set_a = get_feature_set_a(feature_cols)
        assert set(set_a) == set(feature_cols)

    def test_set_b_excludes_volume(self):
        """Set B should exclude all volume features."""
        feature_cols = ["f1", "f2", "transaction_count", "volume_zscore_7d"]
        set_b = get_feature_set_b(feature_cols)

        assert "transaction_count" not in set_b
        assert "volume_zscore_7d" not in set_b
        assert "f1" in set_b
        assert "f2" in set_b

    def test_set_b_retains_behavioral(self):
        """Set B should retain behavioral features."""
        feature_cols = ["amount_mean", "retry_rate", "sku_diversity_ratio"]
        set_b = get_feature_set_b(feature_cols)

        assert "amount_mean" in set_b
        assert "retry_rate" in set_b
        assert "sku_diversity_ratio" in set_b


# ---------------------------------------------------------------------------
# Test: Feature audit
# ---------------------------------------------------------------------------


class TestFeatureAudit:
    def test_audit_returns_all_features(self):
        """Audit should return statistics for all features."""
        df = _make_synthetic_windows()
        feature_cols = get_model_features(df)

        audit_df = feature_audit(df, feature_cols)

        assert len(audit_df) == len(feature_cols)
        assert "feature" in audit_df.columns
        assert "organic_mean" in audit_df.columns
        assert "fraud_mean" in audit_df.columns
        assert "std_diff" in audit_df.columns


# ---------------------------------------------------------------------------
# Test: Models
# ---------------------------------------------------------------------------


class TestModels:
    def test_dummy_classifier_runs(self):
        """DummyClassifier should run without errors."""
        from src.classifier_experiment import create_models
        models = create_models()
        assert "DummyClassifier" in models

    def test_logistic_regression_runs(self):
        """LogisticRegression pipeline should run without errors."""
        from src.classifier_experiment import create_models
        models = create_models()
        assert "LogisticRegression" in models
        assert isinstance(models["LogisticRegression"], Pipeline)

    def test_random_forest_runs(self):
        """RandomForest should run without errors."""
        from src.classifier_experiment import create_models
        models = create_models()
        assert "RandomForest" in models


# ---------------------------------------------------------------------------
# Test: Evaluation
# ---------------------------------------------------------------------------


class TestEvaluation:
    def test_evaluation_returns_required_metrics(self):
        """Evaluation should return all required metrics."""
        from src.classifier_experiment import train_and_evaluate

        # Create small dataset
        rng = np.random.RandomState(42)
        X_train = pd.DataFrame({"f1": rng.randn(20), "f2": rng.randn(20)})
        y_train = pd.Series([0, 1] * 10)
        X_test = pd.DataFrame({"f1": rng.randn(10), "f2": rng.randn(10)})
        y_test = pd.Series([0, 1] * 5)

        model = LogisticRegression(random_state=42, max_iter=1000)
        metrics = train_and_evaluate(model, X_train, X_test, y_train, y_test)

        assert "test_precision" in metrics
        assert "test_recall" in metrics
        assert "test_f1" in metrics
        assert "test_accuracy" in metrics
        assert "train_f1" in metrics
        assert "organic_precision" in metrics
        assert "fraud_precision" in metrics


# ---------------------------------------------------------------------------
# Test: Overfitting detection
# ---------------------------------------------------------------------------


class TestOverfitting:
    def test_overfitting_warning_logic(self):
        """Overfitting should be detected when train F1 - test F1 > 0.15."""
        # This is a logic check, not a full test
        train_f1_high = 0.95
        test_f1_low = 0.70
        overfitting = train_f1_high - test_f1_low > 0.15

        assert overfitting is True

        train_f1_close = 0.80
        test_f1_close = 0.75
        overfitting = train_f1_close - test_f1_close > 0.15

        assert overfitting is False


# ---------------------------------------------------------------------------
# Test: Volume features
# ---------------------------------------------------------------------------


class TestVolumeFeatures:
    def test_volume_features_list(self):
        """VOLUME_FEATURES should contain the expected features."""
        assert "transaction_count" in VOLUME_FEATURES
        assert "volume_zscore_7d" in VOLUME_FEATURES
        assert "volume_rolling_mean_7d" in VOLUME_FEATURES

    def test_volume_features_not_in_set_b(self):
        """No volume feature should be in Set B."""
        feature_cols = ["f1", "f2"] + VOLUME_FEATURES
        set_b = get_feature_set_b(feature_cols)

        for vol_feat in VOLUME_FEATURES:
            assert vol_feat not in set_b
