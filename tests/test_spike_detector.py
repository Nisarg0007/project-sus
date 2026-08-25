"""
Tests for the statistical spike detector module.
"""

import numpy as np
import pandas as pd
import pytest

from src.spike_detector import (
    DEFAULT_Z_THRESHOLD,
    MIN_HISTORY_DAYS,
    compute_historical_baseline,
    detect_spikes,
    evaluate_detection,
    validate_detection_results,
)


# ---------------------------------------------------------------------------
# Test: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_threshold_is_high_recall(self):
        """DEFAULT_Z_THRESHOLD should be 0.5 for high-recall Stage 1 trigger."""
        assert DEFAULT_Z_THRESHOLD == 0.5

    def test_min_history_days(self):
        """MIN_HISTORY_DAYS should be 3."""
        assert MIN_HISTORY_DAYS == 3


# ---------------------------------------------------------------------------
# Helper: Create small synthetic DataFrames for testing
# ---------------------------------------------------------------------------


def _make_windows(
    merchant_id: str = "m1",
    days: int = 10,
    base_volume: int = 100,
    spike_day: int = None,
    spike_multiplier: float = 5.0,
    labels: list[str] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Create a small synthetic window DataFrame with realistic variation."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2025-01-01", periods=days)
    # Add variation to base volume (±10%)
    volumes = [int(base_volume * (1 + rng.uniform(-0.1, 0.1))) for _ in range(days)]

    if spike_day is not None and spike_day < days:
        volumes[spike_day] = int(base_volume * spike_multiplier)

    if labels is None:
        labels = ["baseline"] * days
        if spike_day is not None and spike_day < days:
            labels[spike_day] = "organic_spike"

    # Compute historical baselines manually for test data
    rolling_mean = np.zeros(days)
    rolling_std = np.zeros(days)
    zscore = np.zeros(days)
    ratio_to_mean = np.zeros(days)

    for i in range(days):
        start_idx = max(0, i - 7)
        prior_counts = volumes[start_idx:i]

        if len(prior_counts) == 0:
            rolling_mean[i] = volumes[i]
            rolling_std[i] = 0.0
            zscore[i] = 0.0
            ratio_to_mean[i] = 1.0
        else:
            mean_val = np.mean(prior_counts)
            std_val = np.std(prior_counts, ddof=1) if len(prior_counts) > 1 else 0.0

            rolling_mean[i] = mean_val
            rolling_std[i] = std_val

            if std_val > 0:
                zscore[i] = (volumes[i] - mean_val) / std_val
            else:
                zscore[i] = 0.0

            if mean_val > 0:
                ratio_to_mean[i] = volumes[i] / mean_val
            else:
                ratio_to_mean[i] = 1.0

    return pd.DataFrame({
        "merchant_id": [merchant_id] * days,
        "date": dates,
        "window_label": labels,
        "transaction_count": volumes,
        "volume_rolling_mean_7d": rolling_mean,
        "volume_rolling_std_7d": rolling_std,
        "volume_zscore_7d": zscore,
        "volume_ratio_to_7d_mean": ratio_to_mean,
    })


def _make_multi_merchant_windows(
    merchants: list[str] = None,
    days: int = 10,
    base_volume: int = 100,
) -> pd.DataFrame:
    """Create windows for multiple merchants."""
    if merchants is None:
        merchants = ["m1", "m2", "m3"]

    all_dfs = []
    for i, merchant_id in enumerate(merchants):
        # Different base volumes for each merchant
        merchant_volume = base_volume * (i + 1)
        df = _make_windows(merchant_id=merchant_id, days=days, base_volume=merchant_volume)
        all_dfs.append(df)

    return pd.concat(all_dfs, ignore_index=True)


# ---------------------------------------------------------------------------
# Test: compute_historical_baseline
# ---------------------------------------------------------------------------


class TestHistoricalBaseline:
    def test_excludes_current_day(self):
        """Current day's value should not affect its own baseline."""
        # Create data with variation and a spike on day 5
        rng = np.random.RandomState(42)
        base_values = [100 + int(rng.uniform(-10, 10)) for _ in range(5)]  # Days 1-5
        data = {
            "date": pd.date_range("2025-01-01", periods=10),
            "transaction_count": base_values + [1000] + [100 + int(rng.uniform(-10, 10)) for _ in range(4)],
        }
        df = pd.DataFrame(data)

        result = compute_historical_baseline(df)

        # Day 5 (index 5) has spike of 1000, but its baseline should be based on days 1-5
        # Mean of days 1-5 should be around 100
        assert abs(result.loc[5, "volume_rolling_mean_7d"] - 100) < 20
        # The spike should create a high z-score (since prior values have variation)
        assert result.loc[5, "volume_zscore_7d"] > 2.0

    def test_first_day_defaults(self):
        """First day should have safe defaults."""
        data = {
            "date": pd.date_range("2025-01-01", periods=3),
            "transaction_count": [100, 200, 300],
        }
        df = pd.DataFrame(data)

        result = compute_historical_baseline(df)

        # First day should use its own value as baseline
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

        result = compute_historical_baseline(df)

        # Day 3 (index 2) rolling mean should use only days 1-2
        assert result.loc[2, "volume_rolling_mean_7d"] == 15.0  # (10+20)/2

        # Day 5 (index 4) rolling mean should use only days 1-4
        assert result.loc[4, "volume_rolling_mean_7d"] == 25.0  # (10+20+30+40)/4

    def test_zero_standard_deviation(self):
        """Zero historical standard deviation should be handled safely."""
        data = {
            "date": pd.date_range("2025-01-01", periods=5),
            "transaction_count": [100, 100, 100, 100, 200],
        }
        df = pd.DataFrame(data)

        result = compute_historical_baseline(df)

        # Days 1-4 have identical values, so std should be 0
        assert result.loc[3, "volume_rolling_std_7d"] == 0.0
        # Z-score should be 0 when std is 0
        assert result.loc[3, "volume_zscore_7d"] == 0.0


# ---------------------------------------------------------------------------
# Test: detect_spikes
# ---------------------------------------------------------------------------


class TestDetectSpikes:
    def test_normal_volume_not_flagged(self):
        """Normal volume should not be flagged as a spike."""
        df = _make_windows(days=10, base_volume=100)
        result = detect_spikes(df, z_threshold=2.0, min_history_days=3)

        # After 3 days, normal volume should not trigger
        sufficient_history = result[result["has_sufficient_history"]]
        assert not sufficient_history["is_spike"].any()

    def test_large_volume_jump_flagged(self):
        """A large volume jump should be flagged."""
        df = _make_windows(days=10, base_volume=100, spike_day=5, spike_multiplier=5.0)
        result = detect_spikes(df, z_threshold=2.0, min_history_days=3)

        # Day 5 should be flagged (use == instead of is for numpy booleans)
        assert result.loc[5, "is_spike"] == True

    def test_insufficient_history_not_flagged(self):
        """Windows without sufficient history should not be flagged."""
        df = _make_windows(days=3, base_volume=100, spike_day=2, spike_multiplier=10.0)
        result = detect_spikes(df, z_threshold=2.0, min_history_days=3)

        # Day 2 has only 2 days of history, should not be flagged (use == instead of is)
        assert result.loc[2, "has_sufficient_history"] == False
        assert result.loc[2, "is_spike"] == False

    def test_custom_threshold_changes_behavior(self):
        """Different thresholds should change detection behavior."""
        df = _make_windows(days=10, base_volume=100, spike_day=5, spike_multiplier=3.0)

        # Low threshold: more likely to flag
        result_low = detect_spikes(df, z_threshold=1.0, min_history_days=3)

        # High threshold: less likely to flag
        result_high = detect_spikes(df, z_threshold=3.0, min_history_days=3)

        # Low threshold should detect more spikes
        assert result_low["is_spike"].sum() >= result_high["is_spike"].sum()

    def test_multiple_merchants(self):
        """Detection should work independently for each merchant."""
        df = _make_multi_merchant_windows(merchants=["m1", "m2"], days=10, base_volume=100)
        result = detect_spikes(df, z_threshold=2.0, min_history_days=3)

        # Should have results for both merchants
        assert len(result["merchant_id"].unique()) == 2

    def test_no_nan_values(self):
        """Output should have no NaN values."""
        df = _make_windows(days=10, base_volume=100)
        result = detect_spikes(df, z_threshold=2.0, min_history_days=3)

        assert not result.isnull().any().any()

    def test_no_infinite_values(self):
        """Output should have no infinite values."""
        df = _make_windows(days=10, base_volume=100)
        result = detect_spikes(df, z_threshold=2.0, min_history_days=3)

        numeric_cols = result.select_dtypes(include=[np.number]).columns
        assert not np.isinf(result[numeric_cols]).any().any()


# ---------------------------------------------------------------------------
# Test: Label independence
# ---------------------------------------------------------------------------


class TestLabelIndependence:
    def test_changing_label_does_not_change_detection(self):
        """Detection should not depend on window_label."""
        # Create two identical datasets with different labels
        df1 = _make_windows(days=10, base_volume=100, spike_day=5, spike_multiplier=5.0,
                           labels=["baseline"] * 10)
        df2 = _make_windows(days=10, base_volume=100, spike_day=5, spike_multiplier=5.0,
                           labels=["fraud_spike"] * 10)

        result1 = detect_spikes(df1, z_threshold=2.0, min_history_days=3)
        result2 = detect_spikes(df2, z_threshold=2.0, min_history_days=3)

        # Detection results should be identical
        assert (result1["is_spike"] == result2["is_spike"]).all()
        assert (result1["has_sufficient_history"] == result2["has_sufficient_history"]).all()


# ---------------------------------------------------------------------------
# Test: evaluate_detection
# ---------------------------------------------------------------------------


class TestEvaluateDetection:
    def test_correct_mapping(self):
        """Should correctly map organic_spike and fraud_spike to positive class."""
        detection_results = pd.DataFrame({
            "merchant_id": ["m1"] * 6,
            "date": pd.date_range("2025-01-01", periods=6),
            "window_label": ["baseline", "organic_spike", "fraud_spike",
                           "baseline", "organic_spike", "fraud_spike"],
            "is_spike": [False, True, True, False, False, True],
            "has_sufficient_history": [True] * 6,
        })

        metrics = evaluate_detection(detection_results)

        # True positives: organic_spike + fraud_spike detected
        assert metrics["true_positives"] == 3

        # False negatives: organic_spike or fraud_spike not detected
        assert metrics["false_negatives"] == 1

        # True negatives: baseline not detected
        assert metrics["true_negatives"] == 2

        # False positives: baseline detected
        assert metrics["false_positives"] == 0

    def test_organic_and_fraud_recall(self):
        """Should calculate organic and fraud recall separately."""
        detection_results = pd.DataFrame({
            "merchant_id": ["m1"] * 6,
            "date": pd.date_range("2025-01-01", periods=6),
            "window_label": ["organic_spike", "organic_spike", "organic_spike",
                           "fraud_spike", "fraud_spike", "fraud_spike"],
            "is_spike": [True, True, False, True, False, False],
            "has_sufficient_history": [True] * 6,
        })

        metrics = evaluate_detection(detection_results)

        # Organic recall: 2/3
        assert abs(metrics["organic_recall"] - 2/3) < 1e-10

        # Fraud recall: 1/3
        assert abs(metrics["fraud_recall"] - 1/3) < 1e-10


# ---------------------------------------------------------------------------
# Test: validate_detection_results
# ---------------------------------------------------------------------------


class TestValidateDetectionResults:
    def test_valid_results_pass(self):
        """Valid results should pass validation."""
        df = _make_windows(days=10, base_volume=100)
        detection_results = detect_spikes(df, z_threshold=2.0, min_history_days=3)
        errors = validate_detection_results(detection_results, df)
        assert errors == []

    def test_detects_missing_columns(self):
        """Should detect missing required columns."""
        df = pd.DataFrame({"merchant_id": ["m1"], "date": ["2025-01-01"]})
        input_df = pd.DataFrame({"merchant_id": ["m1"], "date": ["2025-01-01"]})
        errors = validate_detection_results(df, input_df)
        assert any("Missing" in e for e in errors)

    def test_detects_insufficient_history_spike(self):
        """Should detect if windows without sufficient history are flagged."""
        # Create a result where insufficient history window is flagged
        detection_results = pd.DataFrame({
            "merchant_id": ["m1"],
            "date": ["2025-01-01"],
            "window_label": ["baseline"],
            "transaction_count": [100],
            "volume_rolling_mean_7d": [100],
            "volume_rolling_std_7d": [0],
            "volume_zscore_7d": [0],
            "volume_ratio_to_7d_mean": [1],
            "has_sufficient_history": [False],
            "is_spike": [True],  # Should not happen
        })
        input_df = detection_results.copy()
        errors = validate_detection_results(detection_results, input_df)
        assert any("sufficient history" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Test: Leakage prevention
# ---------------------------------------------------------------------------


class TestLeakagePrevention:
    def test_current_day_does_not_affect_own_baseline(self):
        """Changing the current day should not change its own baseline."""
        # Create data with normal values except last day
        data_normal = {
            "date": pd.date_range("2025-01-01", periods=10),
            "transaction_count": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        }
        df_normal = pd.DataFrame(data_normal)

        # Create data with spike on last day
        data_spike = {
            "date": pd.date_range("2025-01-01", periods=10),
            "transaction_count": [100, 100, 100, 100, 100, 100, 100, 100, 100, 1000],
        }
        df_spike = pd.DataFrame(data_spike)

        # Both should have same baselines for days 1-9
        # Day 10 baselines should also be the same (based on days 1-9)
        result_normal = compute_historical_baseline(df_normal)
        result_spike = compute_historical_baseline(df_spike)

        # Day 10 baseline should be identical in both cases
        assert result_normal.loc[9, "volume_rolling_mean_7d"] == result_spike.loc[9, "volume_rolling_mean_7d"]
        assert result_normal.loc[9, "volume_rolling_std_7d"] == result_spike.loc[9, "volume_rolling_std_7d"]


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_all_zero_volumes(self):
        """Should handle all zero volumes gracefully."""
        data = {
            "date": pd.date_range("2025-01-01", periods=5),
            "transaction_count": [0, 0, 0, 0, 0],
        }
        df = pd.DataFrame(data)

        result = compute_historical_baseline(df)

        # Should not crash, all ratios should be 0 or 1
        assert not result.isnull().any().any()
        assert not np.isinf(result.select_dtypes(include=[np.number])).any().any()

    def test_single_day_history(self):
        """Should handle single day of history."""
        data = {
            "date": pd.date_range("2025-01-01", periods=2),
            "transaction_count": [100, 200],
        }
        df = pd.DataFrame(data)

        result = compute_historical_baseline(df)

        # Second day should have mean of 100
        assert result.loc[1, "volume_rolling_mean_7d"] == 100.0
