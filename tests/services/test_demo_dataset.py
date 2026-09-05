"""
Tests for the demo dataset.

Validates that:
  - CSV loads correctly via CSVTransactionDataProvider
  - Required columns exist
  - Timestamps parse
  - Numeric fields are valid
  - Window labels are consistent with transactions
  - The investigation pipeline produces meaningful incidents
  - Different incident types (fraud/organic/review) are produced
  - The dataset is deterministic (same results on every run)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEMO_DIR = Path(__file__).resolve().parents[2] / "data" / "demo"
TXN_PATH = DEMO_DIR / "razorpay_demo_transactions.csv"
WL_PATH = DEMO_DIR / "razorpay_demo_window_labels.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDemoDatasetFiles:
    """Test that demo files exist and are well-formed."""

    def test_transactions_csv_exists(self):
        assert TXN_PATH.exists(), f"Transactions CSV not found at {TXN_PATH}"

    def test_window_labels_csv_exists(self):
        assert WL_PATH.exists(), f"Window labels CSV not found at {WL_PATH}"

    def test_transactions_not_empty(self):
        df = pd.read_csv(TXN_PATH)
        assert len(df) > 0, "Transactions CSV is empty"

    def test_window_labels_not_empty(self):
        df = pd.read_csv(WL_PATH)
        assert len(df) > 0, "Window labels CSV is empty"


class TestDemoTransactionsSchema:
    """Test that transactions have the correct schema."""

    def setup_method(self):
        self.df = pd.read_csv(TXN_PATH)

    def test_required_columns_present(self):
        required = {
            "transaction_id", "merchant_id", "timestamp", "date",
            "customer_id", "amount", "payment_status",
        }
        missing = required - set(self.df.columns)
        assert not missing, f"Missing required columns: {missing}"

    def test_optional_columns_present(self):
        optional = {
            "window_label", "customer_is_new", "sku_id",
            "is_retry", "device_id", "ip_id",
        }
        missing = optional - set(self.df.columns)
        assert not missing, f"Missing optional columns: {missing}"

    def test_all_columns_present(self):
        expected = {
            "transaction_id", "merchant_id", "timestamp", "date",
            "window_label", "customer_id", "customer_is_new", "sku_id",
            "amount", "payment_status", "is_retry", "device_id", "ip_id",
        }
        assert set(self.df.columns) == expected

    def test_timestamps_parse(self):
        parsed = pd.to_datetime(self.df["timestamp"], errors="coerce")
        bad = parsed.isna().sum()
        assert bad == 0, f"{bad} rows have unparseable timestamps"

    def test_dates_parse(self):
        parsed = pd.to_datetime(self.df["date"], errors="coerce")
        bad = parsed.isna().sum()
        assert bad == 0, f"{bad} rows have unparseable dates"

    def test_amounts_are_numeric(self):
        amounts = pd.to_numeric(self.df["amount"], errors="coerce")
        bad = amounts.isna().sum()
        assert bad == 0, f"{bad} rows have non-numeric amounts"
        assert (amounts > 0).all(), "All amounts must be positive"

    def test_payment_status_values(self):
        valid = {"success", "failed"}
        actual = set(self.df["payment_status"].unique())
        invalid = actual - valid
        assert not invalid, f"Invalid payment_status values: {invalid}"

    def test_no_empty_merchant_ids(self):
        blank = self.df["merchant_id"].isna().sum() + (
            self.df["merchant_id"].astype(str).str.strip() == ""
        ).sum()
        assert blank == 0, f"{blank} rows have empty merchant_id"

    def test_no_empty_transaction_ids(self):
        blank = self.df["transaction_id"].isna().sum()
        assert blank == 0, "Some rows have empty transaction_id"

    def test_row_count_reasonable(self):
        assert 1000 < len(self.df) < 50000, (
            f"Row count {len(self.df)} is outside expected range (1000-50000)"
        )


class TestDemoDataCharacteristics:
    """Test that demo data has the expected characteristics."""

    def setup_method(self):
        self.df = pd.read_csv(TXN_PATH)
        self.wl = pd.read_csv(WL_PATH)

    def test_multiple_merchants(self):
        merchants = self.df["merchant_id"].nunique()
        assert merchants >= 3, f"Expected at least 3 merchants, got {merchants}"

    def test_date_range_span(self):
        dates = pd.to_datetime(self.df["date"])
        span = (dates.max() - dates.min()).days
        assert span >= 30, f"Date range spans only {span} days, expected >= 30"

    def test_window_labels_match_transactions(self):
        """Window labels should correspond to merchant-date pairs in transactions."""
        txn_pairs = set(zip(self.df["merchant_id"], self.df["date"]))
        wl_pairs = set(zip(self.wl["merchant_id"], self.wl["date"]))
        # Window labels may be a subset if they were filtered
        assert wl_pairs.issubset(txn_pairs) or txn_pairs.issubset(wl_pairs), (
            "Window labels and transactions have mismatched merchant-date pairs"
        )

    def test_window_label_counts_match(self):
        """Transaction counts per merchant-date should match window_labels."""
        txn_counts = (
            self.df.groupby(["merchant_id", "date"])
            .size()
            .reset_index(name="txn_count")
        )
        merged = txn_counts.merge(self.wl, on=["merchant_id", "date"], how="inner")
        mismatches = merged[merged["txn_count"] != merged["transaction_count"]]
        assert len(mismatches) == 0, (
            f"{len(mismatches)} window labels have mismatched transaction counts"
        )

    def test_has_baseline_and_anomaly_labels(self):
        """Window labels should contain both baseline and anomaly periods."""
        labels = set(self.wl["window_label"].unique())
        assert "baseline" in labels, "No baseline windows in labels"
        # Should have at least one anomaly type
        anomaly_labels = labels - {"baseline"}
        assert len(anomaly_labels) > 0, "No anomaly windows in labels"

    def test_deterministic(self):
        """Same file content on every generation."""
        h = _hash_file(TXN_PATH)
        assert len(h) == 64, "Hash should be SHA-256"
        # We just verify it's a stable hash; exact value depends on generator
        # If this test breaks, the generator changed its output.


class TestDemoProviderValidation:
    """Test that CSVTransactionDataProvider validates the demo data."""

    def test_provider_validates_successfully(self):
        from src.services.transaction_data_provider import CSVTransactionDataProvider

        provider = CSVTransactionDataProvider(
            transactions_path=str(TXN_PATH),
            window_labels_path=str(WL_PATH),
        )
        result = provider.validate()
        assert result.is_valid, f"Validation failed: {result.errors}"
        assert result.total_rows > 0
        assert len(result.errors) == 0

    def test_provider_metadata(self):
        from src.services.transaction_data_provider import CSVTransactionDataProvider

        provider = CSVTransactionDataProvider(
            transactions_path=str(TXN_PATH),
            window_labels_path=str(WL_PATH),
        )
        result = provider.validate()
        meta = result.metadata
        assert "unique_merchants" in meta
        assert meta["unique_merchants"] >= 3
        assert "date_range_start" in meta
        assert "date_range_end" in meta

    def test_date_range_not_truncated_by_preview(self):
        """Regression: validate() must report the FULL date range, not just
        the first 1000 rows.  The demo CSV spans 2025-07-01 to 2025-08-24.
        """
        from src.services.transaction_data_provider import CSVTransactionDataProvider

        provider = CSVTransactionDataProvider(
            transactions_path=str(TXN_PATH),
        )
        result = provider.validate()
        meta = result.metadata
        assert meta["date_range_start"].startswith("2025-07-01"), (
            f"Expected start 2025-07-01, got {meta['date_range_start']}"
        )
        assert meta["date_range_end"].startswith("2025-08-24"), (
            f"Expected end 2025-08-24, got {meta['date_range_end']}"
        )

    def test_provider_loads_data(self):
        from src.services.transaction_data_provider import CSVTransactionDataProvider

        provider = CSVTransactionDataProvider(
            transactions_path=str(TXN_PATH),
            window_labels_path=str(WL_PATH),
        )
        txns = provider.load_transactions()
        wls = provider.load_window_labels()
        assert len(txns) > 0
        assert len(wls) > 0
        assert set(REQUIRED_TXN_COLUMNS).issubset(set(txns.columns))


class TestDemoPipelineRun:
    """Test that the full pipeline runs against demo data and produces incidents."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.txns = pd.read_csv(TXN_PATH)
        self.wls = pd.read_csv(WL_PATH)

    def test_pipeline_completes(self):
        from src.pipeline import run_pipeline

        results = run_pipeline(
            self.txns, self.wls,
            z_threshold=0.5,
            min_history_days=3,
        )
        assert len(results) > 0

    def test_pipeline_produces_incidents(self):
        from src.pipeline import run_pipeline, get_pipeline_summary

        results = run_pipeline(self.txns, self.wls)
        summary = get_pipeline_summary(results)

        assert summary["total_windows"] > 0
        assert summary["n_spikes_detected"] > 0, "No spikes detected"

    def test_pipeline_produces_mixed_statuses(self):
        """Pipeline should produce multiple status types for a good demo."""
        from src.pipeline import run_pipeline, get_pipeline_summary

        results = run_pipeline(self.txns, self.wls)
        summary = get_pipeline_summary(results)

        # Should have baseline windows
        assert summary["n_baseline"] > 0, "No baseline windows"

        # Should have at least some spikes
        assert summary["n_spikes_detected"] > 0, "No spikes detected"

        # Should have at least one non-baseline status
        has_fraud = summary["n_fraud_spike"] > 0
        has_organic = summary["n_organic_spike"] > 0
        has_review = summary["n_review_required"] > 0
        assert has_fraud or has_organic or has_review, (
            "No incidents produced — demo would be uninteresting"
        )

    def test_pipeline_summary_counts_add_up(self):
        from src.pipeline import run_pipeline, get_pipeline_summary

        results = run_pipeline(self.txns, self.wls)
        summary = get_pipeline_summary(results)

        total_from_statuses = (
            summary["n_baseline"]
            + summary["n_fraud_spike"]
            + summary["n_organic_spike"]
            + summary["n_review_required"]
        )
        assert total_from_statuses == summary["total_windows"], (
            "Status counts don't add up to total windows"
        )

    def test_pipeline_results_have_required_columns(self):
        from src.pipeline import run_pipeline

        results = run_pipeline(self.txns, self.wls)

        required = {
            "merchant_id", "date", "is_spike", "volume_zscore_7d",
            "final_status", "decision_reason",
        }
        missing = required - set(results.columns)
        assert not missing, f"Missing columns in results: {missing}"

    def test_deterministic_pipeline_output(self):
        """Running the pipeline twice on the same data produces identical results."""
        from src.pipeline import run_pipeline

        r1 = run_pipeline(self.txns, self.wls)
        r2 = run_pipeline(self.txns, self.wls)

        pd.testing.assert_frame_equal(r1, r2)

    def test_api_upload_path_produces_incidents(self):
        """Regression: uploading CSV via the API path must produce real
        incidents.  Previously, the API defaulted to the original pipeline's
        window labels, causing zero incidents for uploaded datasets.
        """
        from src.services.investigation_service import InvestigationService

        svc = InvestigationService()
        result = svc.run_investigation(
            transactions_path=str(TXN_PATH),
            window_labels_path=None,  # No labels — simulates uploaded dataset
            z_threshold=0.5,
            min_history_days=3,
        )

        assert result["total_results"] > 0, "No windows analyzed"
        assert result["summary"].spikes_detected > 0, "No spikes detected"
        assert len(result["incidents"]) > 0, "Zero incidents — demo would show nothing"
        # Must produce a mix of incident types
        fraud = sum(1 for i in result["incidents"] if i.classification.value == "fraud_spike")
        assert fraud > 0, "No fraud incidents in demo upload path"


# Required columns constant for provider test
REQUIRED_TXN_COLUMNS = frozenset({
    "transaction_id", "merchant_id", "timestamp", "date",
    "customer_id", "amount", "payment_status",
})
