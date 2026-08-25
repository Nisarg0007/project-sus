"""
Tests for the window-level feature engineering module.
"""

import numpy as np
import pandas as pd
import pytest

from src.features import (
    build_window_features,
    compute_concentration_metrics,
    compute_historical_features,
    compute_window_features,
    get_feature_columns,
    safe_division,
    shannon_entropy,
    validate_features,
)


# ---------------------------------------------------------------------------
# Helper: Create small synthetic DataFrames for testing
# ---------------------------------------------------------------------------


def _make_transactions(n: int = 10, merchant_id: str = "m1", date: str = "2025-01-01",
                       label: str = "baseline", seed: int = 42) -> pd.DataFrame:
    """Create a small synthetic transaction DataFrame."""
    rng = np.random.RandomState(seed)
    return pd.DataFrame({
        "transaction_id": [f"txn_{i}" for i in range(n)],
        "merchant_id": [merchant_id] * n,
        "timestamp": pd.date_range(date, periods=n, freq="h"),
        "date": [date] * n,
        "window_label": [label] * n,
        "customer_id": [f"cust_{i % 3}" for i in range(n)],
        "customer_is_new": [i % 3 == 0 for i in range(n)],
        "sku_id": [f"sku_{i % 4}" for i in range(n)],
        "amount": rng.uniform(10, 100, n).round(2),
        "payment_status": ["success"] * (n - 2) + ["failed"] * 2,
        "is_retry": [False] * (n - 1) + [True],
        "device_id": [f"dev_{i % 5}" for i in range(n)],
        "ip_id": [f"ip_{i % 4}" for i in range(n)],
    })


def _make_multi_day_transactions(merchant_id: str = "m1", days: int = 10,
                                  seed: int = 42) -> pd.DataFrame:
    """Create transactions across multiple days."""
    rng = np.random.RandomState(seed)
    all_txns = []
    for d in range(days):
        date = f"2025-01-{d + 1:02d}"
        n_txns = rng.randint(50, 100)
        txn = _make_transactions(n=n_txns, merchant_id=merchant_id, date=date, seed=seed + d)
        all_txns.append(txn)
    return pd.concat(all_txns, ignore_index=True)


# ---------------------------------------------------------------------------
# Test: safe_division
# ---------------------------------------------------------------------------


class TestSafeDivision:
    def test_normal_division(self):
        assert safe_division(10, 2) == 5.0

    def test_zero_denominator(self):
        assert safe_division(10, 0) == 0.0

    def test_custom_default(self):
        assert safe_division(10, 0, default=-1.0) == -1.0

    def test_nan_numerator(self):
        result = safe_division(float("nan"), 10)
        assert result == 0.0


# ---------------------------------------------------------------------------
# Test: shannon_entropy
# ---------------------------------------------------------------------------


class TestShannonEntropy:
    def test_uniform_distribution(self):
        counts = np.array([1, 1, 1, 1])
        entropy = shannon_entropy(counts)
        assert abs(entropy - 2.0) < 1e-10  # log2(4) = 2.0

    def test_single_element(self):
        counts = np.array([10])
        entropy = shannon_entropy(counts)
        assert abs(entropy - 0.0) < 1e-10

    def test_empty_array(self):
        entropy = shannon_entropy(np.array([]))
        assert entropy == 0.0

    def test_two_elements_unequal(self):
        counts = np.array([3, 1])
        entropy = shannon_entropy(counts)
        assert entropy > 0
        assert entropy < 1.0  # Less than log2(2) = 1.0


# ---------------------------------------------------------------------------
# Test: compute_concentration_metrics
# ---------------------------------------------------------------------------


class TestConcentrationMetrics:
    def test_uniform_distribution(self):
        values = pd.Series(["a", "b", "c", "d"])
        unique_count, diversity, top_share, entropy = compute_concentration_metrics(values)
        assert unique_count == 4
        assert abs(diversity - 1.0) < 1e-10
        assert abs(top_share - 0.25) < 1e-10
        assert abs(entropy - 2.0) < 1e-10

    def test_concentrated_distribution(self):
        values = pd.Series(["a", "a", "a", "a", "b"])
        unique_count, diversity, top_share, entropy = compute_concentration_metrics(values)
        assert unique_count == 2
        assert abs(top_share - 0.8) < 1e-10

    def test_empty_series(self):
        values = pd.Series([], dtype=str)
        unique_count, diversity, top_share, entropy = compute_concentration_metrics(values)
        assert unique_count == 0
        assert diversity == 0.0


# ---------------------------------------------------------------------------
# Test: compute_window_features
# ---------------------------------------------------------------------------


class TestWindowFeatures:
    def test_basic_feature_computation(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        assert features["transaction_count"] == 10
        assert features["successful_transaction_count"] == 8
        assert features["failed_transaction_count"] == 2
        assert abs(features["success_rate"] - 0.8) < 1e-10
        assert abs(features["failed_payment_rate"] - 0.2) < 1e-10

    def test_amount_features(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        assert "amount_mean" in features
        assert "amount_median" in features
        assert "amount_std" in features
        assert "amount_min" in features
        assert "amount_max" in features
        assert "amount_p25" in features
        assert "amount_p75" in features
        assert "amount_iqr" in features
        assert "amount_cv" in features
        assert features["amount_min"] > 0
        assert features["amount_max"] > features["amount_min"]

    def test_sku_diversity(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        assert "unique_sku_count" in features
        assert "sku_diversity_ratio" in features
        assert "top_sku_share" in features
        assert "sku_entropy" in features
        assert 0 <= features["sku_diversity_ratio"] <= 1
        assert 0 <= features["top_sku_share"] <= 1

    def test_retry_features(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        assert features["retry_count"] == 1
        assert features["retry_rate"] == 0.1
        assert features["failed_retry_count"] <= features["retry_count"]
        assert 0 <= features["failed_retry_rate"] <= 1

    def test_device_ip_features(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        assert "unique_device_count" in features
        assert "device_diversity_ratio" in features
        assert "unique_ip_count" in features
        assert "ip_diversity_ratio" in features
        assert 0 <= features["device_diversity_ratio"] <= 1
        assert 0 <= features["ip_diversity_ratio"] <= 1

    def test_customer_features(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        assert "unique_customer_count" in features
        assert "customer_diversity_ratio" in features
        assert "new_customer_share" in features
        assert "repeat_customer_share" in features
        assert 0 <= features["new_customer_share"] <= 1
        assert 0 <= features["repeat_customer_share"] <= 1

    def test_rate_sums_to_one(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        # success_rate + failed_payment_rate should be approximately 1
        assert abs(features["success_rate"] + features["failed_payment_rate"] - 1.0) < 1e-10

    def test_customer_shares_sum_to_one(self):
        txn = _make_transactions(n=10)
        features = compute_window_features(txn)

        # new_customer_share + repeat_customer_share should be approximately 1
        assert abs(features["new_customer_share"] + features["repeat_customer_share"] - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# Test: compute_historical_features
# ---------------------------------------------------------------------------


class TestHistoricalFeatures:
    def test_excludes_current_day(self):
        """Changing the current day's count should not change its rolling baseline."""
        # Create a merchant with 10 days of history
        data = {
            "date": pd.date_range("2025-01-01", periods=10),
            "transaction_count": [100, 110, 90, 120, 100, 115, 95, 105, 110, 1000],  # Day 10 is spike
        }
        df = pd.DataFrame(data)

        # Compute historical features
        result = compute_historical_features(df)

        # Day 10 (index 9) rolling mean should be based on days 1-9 only
        # Mean of days 1-9: (100+110+90+120+100+115+95+105+110)/9 ≈ 104.4
        assert result.loc[9, "volume_rolling_mean_7d"] < 500  # Not influenced by day 10's spike
        assert result.loc[9, "volume_rolling_mean_7d"] > 50  # But still reasonable

    def test_no_leakage_final_day(self):
        """Final day's volume should not affect its own baseline."""
        data = {
            "date": pd.date_range("2025-01-01", periods=5),
            "transaction_count": [100, 100, 100, 100, 9999],
        }
        df = pd.DataFrame(data)

        result = compute_historical_features(df)

        # Day 5 rolling mean should use only days 1-4
        assert result.loc[4, "volume_rolling_mean_7d"] == 100.0
        assert result.loc[4, "volume_rolling_std_7d"] == 0.0
        # Z-score and ratio may change based on current value vs historical baseline
        # But the baseline itself should be unaffected

    def test_first_day_defaults(self):
        """First day should have safe defaults since there's no history."""
        data = {
            "date": pd.date_range("2025-01-01", periods=3),
            "transaction_count": [100, 200, 300],
        }
        df = pd.DataFrame(data)

        result = compute_historical_features(df)

        # First day should have sensible defaults
        assert result.loc[0, "volume_rolling_mean_7d"] == 100.0
        assert result.loc[0, "volume_rolling_std_7d"] == 0.0
        assert result.loc[0, "volume_zscore_7d"] == 0.0
        assert result.loc[0, "volume_ratio_to_7d_mean"] == 1.0

    def test_rolling_mean_uses_only_prior_days(self):
        """Rolling mean at day t uses only days < t."""
        data = {
            "date": pd.date_range("2025-01-01", periods=5),
            "transaction_count": [10, 20, 30, 40, 50],
        }
        df = pd.DataFrame(data)

        result = compute_historical_features(df)

        # Day 3 (index 2) rolling mean should use only days 1-2
        assert result.loc[2, "volume_rolling_mean_7d"] == 15.0  # (10+20)/2

        # Day 5 (index 4) rolling mean should use only days 1-4
        assert result.loc[4, "volume_rolling_mean_7d"] == 25.0  # (10+20+30+40)/4


# ---------------------------------------------------------------------------
# Test: build_window_features (integration)
# ---------------------------------------------------------------------------


class TestBuildWindowFeatures:
    def test_correct_window_count(self):
        """Should produce one row per merchant-date."""
        txn = _make_multi_day_transactions(merchant_id="m1", days=5)
        labels = pd.DataFrame({
            "merchant_id": ["m1"] * 5,
            "date": pd.date_range("2025-01-01", periods=5),
            "window_label": ["baseline"] * 5,
            "transaction_count": txn.groupby("date").size().values,
        })

        result = build_window_features(txn, labels)
        assert len(result) == 5

    def test_no_duplicate_windows(self):
        """Each merchant-date should appear exactly once."""
        txn = _make_multi_day_transactions(merchant_id="m1", days=5)
        labels = pd.DataFrame({
            "merchant_id": ["m1"] * 5,
            "date": pd.date_range("2025-01-01", periods=5),
            "window_label": ["baseline"] * 5,
            "transaction_count": txn.groupby("date").size().values,
        })

        result = build_window_features(txn, labels)
        assert not result.duplicated(subset=["merchant_id", "date"]).any()

    def test_no_nan_values(self):
        """Output should have no NaN values."""
        txn = _make_multi_day_transactions(merchant_id="m1", days=10)
        txn_counts = txn.groupby("date").size().reset_index(name="transaction_count")
        labels = pd.DataFrame({
            "merchant_id": ["m1"] * 10,
            "date": pd.date_range("2025-01-01", periods=10),
            "window_label": ["baseline"] * 10,
            "transaction_count": txn_counts["transaction_count"].values,
        })

        result = build_window_features(txn, labels)
        assert not result.isnull().any().any()

    def test_no_infinite_values(self):
        """Output should have no infinite values."""
        txn = _make_multi_day_transactions(merchant_id="m1", days=10)
        txn_counts = txn.groupby("date").size().reset_index(name="transaction_count")
        labels = pd.DataFrame({
            "merchant_id": ["m1"] * 10,
            "date": pd.date_range("2025-01-01", periods=10),
            "window_label": ["baseline"] * 10,
            "transaction_count": txn_counts["transaction_count"].values,
        })

        result = build_window_features(txn, labels)
        numeric_cols = result.select_dtypes(include=[np.number]).columns
        assert not np.isinf(result[numeric_cols]).any().any()

    def test_window_label_preserved(self):
        """window_label should be present in output."""
        txn = _make_transactions(n=10, label="fraud_spike")
        labels = pd.DataFrame({
            "merchant_id": ["m1"],
            "date": ["2025-01-01"],
            "window_label": ["fraud_spike"],
            "transaction_count": [10],
        })

        result = build_window_features(txn, labels)
        assert "window_label" in result.columns
        assert result.loc[0, "window_label"] == "fraud_spike"


# ---------------------------------------------------------------------------
# Test: get_feature_columns
# ---------------------------------------------------------------------------


class TestFeatureColumns:
    def test_excludes_metadata_columns(self):
        df = pd.DataFrame({
            "merchant_id": ["m1"],
            "date": ["2025-01-01"],
            "window_label": ["baseline"],
            "transaction_count": [100],
            "amount_mean": [50.0],
        })

        feature_cols = get_feature_columns(df)
        assert "merchant_id" not in feature_cols
        assert "date" not in feature_cols
        assert "window_label" not in feature_cols
        assert "transaction_count" in feature_cols
        assert "amount_mean" in feature_cols


# ---------------------------------------------------------------------------
# Test: validate_features
# ---------------------------------------------------------------------------


class TestValidateFeatures:
    def test_valid_features_pass(self):
        txn = _make_multi_day_transactions(merchant_id="m1", days=5)
        labels = pd.DataFrame({
            "merchant_id": ["m1"] * 5,
            "date": pd.date_range("2025-01-01", periods=5),
            "window_label": ["baseline"] * 5,
            "transaction_count": txn.groupby("date").size().values,
        })
        result = build_window_features(txn, labels)
        errors = validate_features(result, expected_merchants=1, expected_days=5)
        assert errors == []

    def test_detects_missing_columns(self):
        df = pd.DataFrame({"merchant_id": ["m1"], "date": ["2025-01-01"]})
        errors = validate_features(df, expected_merchants=1, expected_days=1)
        assert any("window_label" in e for e in errors)

    def test_detects_duplicate_windows(self):
        df = pd.DataFrame({
            "merchant_id": ["m1", "m1"],
            "date": ["2025-01-01", "2025-01-01"],
            "window_label": ["baseline", "baseline"],
            "transaction_count": [100, 100],
        })
        errors = validate_features(df, expected_merchants=1, expected_days=1)
        assert any("duplicate" in e.lower() for e in errors)

    def test_detects_wrong_window_count(self):
        df = pd.DataFrame({
            "merchant_id": ["m1", "m1"],
            "date": pd.date_range("2025-01-01", periods=2),
            "window_label": ["baseline", "baseline"],
            "transaction_count": [100, 100],
        })
        errors = validate_features(df, expected_merchants=1, expected_days=5)
        assert any("Expected" in e and "windows" in e for e in errors)


# ---------------------------------------------------------------------------
# Test: Leakage prevention
# ---------------------------------------------------------------------------


class TestLeakagePrevention:
    def test_historical_rolling_excludes_current_day(self):
        """
        Changing the last day's transaction count should NOT change its
        rolling_mean_7d or rolling_std_7d.
        """
        # Create a merchant with 10 days, last day = 100
        data_normal = {
            "date": pd.date_range("2025-01-01", periods=10),
            "transaction_count": [100, 110, 90, 120, 100, 115, 95, 105, 110, 100],
        }
        df_normal = pd.DataFrame(data_normal)
        result_normal = compute_historical_features(df_normal)

        # Now change the last day to 1000 (spike)
        data_spike = {
            "date": pd.date_range("2025-01-01", periods=10),
            "transaction_count": [100, 110, 90, 120, 100, 115, 95, 105, 110, 1000],
        }
        df_spike = pd.DataFrame(data_spike)
        result_spike = compute_historical_features(df_spike)

        # The rolling baseline for the last day should be identical
        assert result_normal.loc[9, "volume_rolling_mean_7d"] == result_spike.loc[9, "volume_rolling_mean_7d"]
        assert result_normal.loc[9, "volume_rolling_std_7d"] == result_spike.loc[9, "volume_rolling_std_7d"]
