"""
Tests for the synthetic transaction data generator.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.generate_data import (
    NUM_DAYS,
    NUM_MERCHANTS,
    create_merchant_profiles,
    generate_transactions,
    save_data,
    schedule_window_labels,
    validate_generated_data,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seed():
    """Default seed for reproducibility tests."""
    return 42


@pytest.fixture
def profiles(seed):
    """Create merchant profiles."""
    return create_merchant_profiles(seed)


@pytest.fixture
def window_labels(profiles, seed):
    """Generate window labels."""
    return schedule_window_labels(profiles, NUM_DAYS, seed)


@pytest.fixture
def transactions(profiles, window_labels, seed):
    """Generate full transaction dataset."""
    return generate_transactions(profiles, window_labels, seed)


@pytest.fixture
def window_labels_df(window_labels, transactions):
    """Convert window labels to DataFrame with transaction counts."""
    df = pd.DataFrame(window_labels)
    # Compute transaction counts per window
    txn_counts = transactions.groupby(["merchant_id", "date"]).size().reset_index(name="transaction_count")
    # Ensure date types match
    df["date"] = pd.to_datetime(df["date"])
    df = df.merge(txn_counts, on=["merchant_id", "date"])
    return df


# ---------------------------------------------------------------------------
# Test: Merchant profiles
# ---------------------------------------------------------------------------

class TestMerchantProfiles:
    def test_correct_merchant_count(self, profiles):
        assert len(profiles) == NUM_MERCHANTS

    def test_unique_merchant_ids(self, profiles):
        ids = [p.merchant_id for p in profiles]
        assert len(set(ids)) == NUM_MERCHANTS

    def test_merchant_ids_follow_naming_convention(self, profiles):
        for p in profiles:
            assert p.merchant_id.startswith("merchant_")

    def test_profiles_have_required_attributes(self, profiles):
        for p in profiles:
            assert p.base_daily_volume > 0
            assert p.amount_min > 0
            assert p.amount_max > p.amount_min
            assert p.catalog_size > 0
            assert p.customer_pool_size > 0
            assert 0 <= p.repeat_customer_rate <= 1
            assert 0 <= p.base_failure_rate <= 1


# ---------------------------------------------------------------------------
# Test: Window labels
# ---------------------------------------------------------------------------

class TestWindowLabels:
    def test_total_window_count(self, window_labels):
        assert len(window_labels) == NUM_MERCHANTS * NUM_DAYS

    def test_all_three_labels_exist(self, window_labels):
        labels = {w["window_label"] for w in window_labels}
        assert labels == {"baseline", "organic_spike", "fraud_spike"}

    def test_baseline_is_majority(self, window_labels):
        from collections import Counter
        counts = Counter(w["window_label"] for w in window_labels)
        assert counts["baseline"] > counts["organic_spike"]
        assert counts["baseline"] > counts["fraud_spike"]

    def test_each_merchant_has_correct_day_count(self, window_labels):
        from collections import Counter
        merchant_days = Counter(w["merchant_id"] for w in window_labels)
        for mid, count in merchant_days.items():
            assert count == NUM_DAYS, f"{mid} has {count} days, expected {NUM_DAYS}"

    def test_no_consecutive_same_label_exceeding_three(self, window_labels):
        """No merchant should have more than 3 consecutive same labels."""
        for merchant_id in set(w["merchant_id"] for w in window_labels):
            merchant_wins = sorted(
                [w for w in window_labels if w["merchant_id"] == merchant_id],
                key=lambda w: w["date"],
            )
            labels = [w["window_label"] for w in merchant_wins]
            # Check runs
            max_run = 1
            current_run = 1
            for i in range(1, len(labels)):
                if labels[i] == labels[i - 1]:
                    current_run += 1
                    max_run = max(max_run, current_run)
                else:
                    current_run = 1
            assert max_run <= 3, (
                f"Merchant {merchant_id} has a run of {max_run} consecutive same labels"
            )


# ---------------------------------------------------------------------------
# Test: Transactions
# ---------------------------------------------------------------------------

class TestTransactions:
    def test_correct_merchant_count(self, transactions):
        assert transactions["merchant_id"].nunique() == NUM_MERCHANTS

    def test_correct_date_count_per_merchant(self, transactions):
        dates_per_merchant = transactions.groupby("merchant_id")["date"].nunique()
        for mid, count in dates_per_merchant.items():
            assert count == NUM_DAYS

    def test_unique_transaction_ids(self, transactions):
        assert not transactions["transaction_id"].duplicated().any()

    def test_positive_amounts(self, transactions):
        assert (transactions["amount"] > 0).all()

    def test_valid_payment_status(self, transactions):
        valid_statuses = {"success", "failed"}
        assert transactions["payment_status"].isin(valid_statuses).all()

    def test_valid_boolean_columns(self, transactions):
        assert transactions["customer_is_new"].dtype == bool
        assert transactions["is_retry"].dtype == bool

    def test_no_null_transaction_ids(self, transactions):
        assert transactions["transaction_id"].notna().all()

    def test_no_null_merchant_ids(self, transactions):
        assert transactions["merchant_id"].notna().all()


# ---------------------------------------------------------------------------
# Test: Window transaction counts
# ---------------------------------------------------------------------------

class TestWindowCounts:
    def test_window_counts_match(self, transactions, window_labels_df):
        txn_counts = (
            transactions.groupby(["merchant_id", "date"])
            .size()
            .reset_index(name="txn_count")
        )
        # Ensure date types match
        txn_counts["date"] = pd.to_datetime(txn_counts["date"])
        merged = window_labels_df.merge(txn_counts, on=["merchant_id", "date"])
        assert (merged["transaction_count"] == merged["txn_count"]).all()


# ---------------------------------------------------------------------------
# Test: Reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility:
    def test_same_seed_same_output(self, seed):
        profiles1 = create_merchant_profiles(seed)
        wl1 = schedule_window_labels(profiles1, NUM_DAYS, seed)
        txn1 = generate_transactions(profiles1, wl1, seed)

        profiles2 = create_merchant_profiles(seed)
        wl2 = schedule_window_labels(profiles2, NUM_DAYS, seed)
        txn2 = generate_transactions(profiles2, wl2, seed)

        pd.testing.assert_frame_equal(txn1, txn2)

    def test_different_seed_different_output(self, seed):
        profiles1 = create_merchant_profiles(seed)
        wl1 = schedule_window_labels(profiles1, NUM_DAYS, seed)
        txn1 = generate_transactions(profiles1, wl1, seed)

        profiles2 = create_merchant_profiles(seed + 1)
        wl2 = schedule_window_labels(profiles2, NUM_DAYS, seed + 1)
        txn2 = generate_transactions(profiles2, wl2, seed + 1)

        # With different seeds, outputs should differ
        assert len(txn1) != len(txn2) or not txn1.equals(txn2)


# ---------------------------------------------------------------------------
# Test: Save and validate
# ---------------------------------------------------------------------------

class TestSaveAndValidate:
    def test_save_creates_files(self, transactions, window_labels_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            txn_path, labels_path = save_data(transactions, window_labels_df, tmpdir)
            assert Path(txn_path).exists()
            assert Path(labels_path).exists()

    def test_validation_passes(self, transactions, window_labels_df):
        errors = validate_generated_data(transactions, window_labels_df)
        assert errors == [], f"Validation errors: {errors}"

    def test_roundtrip_csv(self, transactions, window_labels_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_data(transactions, window_labels_df, tmpdir)
            txn2 = pd.read_csv(Path(tmpdir) / "transactions.csv")
            # Basic shape check
            assert len(txn2) == len(transactions)
            assert list(txn2.columns) == list(transactions.columns)
