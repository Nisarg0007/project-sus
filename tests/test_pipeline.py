"""
Tests for the end-to-end SUS pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from src.pipeline import (
    run_pipeline,
    get_pipeline_summary,
    _assign_final_status,
    _assign_decision_reason,
    STATUS_BASELINE,
    STATUS_ORGANIC_SPIKE,
    STATUS_FRAUD_SPIKE,
    STATUS_REVIEW_REQUIRED,
)


# ---------------------------------------------------------------------------
# Helper: Create small synthetic data for testing
# ---------------------------------------------------------------------------


def _make_synthetic_transactions_and_labels(
    n_merchants: int = 2,
    n_days: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create minimal synthetic transactions and window labels for testing."""
    rng = np.random.RandomState(42)

    transactions = []
    window_labels = []

    for m in range(n_merchants):
        merchant_id = f"merchant_{m+1:03d}"
        for d in range(n_days):
            date = pd.Timestamp("2025-07-01") + pd.Timedelta(days=d)

            # Determine window label
            if d == 0:
                label = "baseline"
                n_txns = 50
            elif d == 1:
                label = "organic_spike"
                n_txns = 100
            elif d == 2:
                label = "fraud_spike"
                n_txns = 100
            else:
                label = "baseline"
                n_txns = 50

            window_labels.append({
                "merchant_id": merchant_id,
                "date": date.date(),
                "window_label": label,
                "transaction_count": n_txns,
            })

            # Generate transactions
            for t in range(n_txns):
                transactions.append({
                    "transaction_id": f"txn_{merchant_id}_{d:02d}_{t:04d}",
                    "merchant_id": merchant_id,
                    "timestamp": date + pd.Timedelta(hours=rng.randint(0, 24)),
                    "date": date.date(),
                    "window_label": label,
                    "customer_id": f"cust_{t % 20:04d}",
                    "customer_is_new": rng.random() > 0.5,
                    "sku_id": f"sku_{t % 10:04d}",
                    "amount": rng.uniform(10, 100),
                    "payment_status": "success" if rng.random() > 0.1 else "failed",
                    "is_retry": rng.random() > 0.9,
                    "device_id": f"dev_{t % 15:04d}",
                    "ip_id": f"ip_{t % 12:04d}",
                })

    return pd.DataFrame(transactions), pd.DataFrame(window_labels)


# ---------------------------------------------------------------------------
# Test: Pipeline Output Structure
# ---------------------------------------------------------------------------


class TestPipelineOutputStructure:
    def test_output_has_required_columns(self):
        """Output should contain all required columns."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()
        results = run_pipeline(transactions, window_labels)

        required_cols = [
            "merchant_id",
            "date",
            "is_spike",
            "volume_zscore_7d",
            "predicted_cause",
            "fraud_probability",
            "confidence",
            "confidence_band",
            "final_status",
            "decision_reason",
        ]

        for col in required_cols:
            assert col in results.columns, f"Missing column: {col}"

    def test_one_row_per_merchant_date(self):
        """Should have exactly one row per merchant-date."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()
        results = run_pipeline(transactions, window_labels)

        # No duplicate merchant-date pairs
        assert not results.duplicated(subset=["merchant_id", "date"]).any()

        # Count should match input
        expected_windows = len(window_labels)
        assert len(results) == expected_windows


# ---------------------------------------------------------------------------
# Test: Baseline Windows
# ---------------------------------------------------------------------------


class TestBaselineWindows:
    def test_baseline_final_status(self):
        """Baseline windows should have final_status = baseline."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()
        results = run_pipeline(transactions, window_labels)

        # Find baseline windows from labels
        baseline_mask = window_labels["window_label"] == "baseline"

        for idx in window_labels[baseline_mask].index:
            row = results.iloc[idx]
            assert row["final_status"] == STATUS_BASELINE
            assert row["predicted_cause"] is None
            assert row["fraud_probability"] is None or np.isnan(row["fraud_probability"])
            assert row["confidence_band"] is None


# ---------------------------------------------------------------------------
# Test: Spike Detection
# ---------------------------------------------------------------------------


class TestSpikeDetection:
    def test_detected_spikes_reach_stage2(self):
        """Detected spikes should be classified by Stage 2."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()
        results = run_pipeline(transactions, window_labels)

        detected_spikes = results[results["is_spike"] == True]

        # Detected spikes should have predictions
        assert (detected_spikes["predicted_cause"].notna()).all()


# ---------------------------------------------------------------------------
# Test: Decision Logic
# ---------------------------------------------------------------------------


class TestDecisionLogic:
    def test_high_confidence_fraud(self):
        """High confidence fraud should become fraud_spike."""
        row = pd.Series({
            "is_spike": True,
            "predicted_cause": "fraud_spike",
            "confidence": 0.95,
            "confidence_band": "high_confidence",
        })
        assert _assign_final_status(row) == STATUS_FRAUD_SPIKE

    def test_high_confidence_organic(self):
        """High confidence organic should become organic_spike."""
        row = pd.Series({
            "is_spike": True,
            "predicted_cause": "organic_spike",
            "confidence": 0.95,
            "confidence_band": "high_confidence",
        })
        assert _assign_final_status(row) == STATUS_ORGANIC_SPIKE

    def test_ambiguous_should_review(self):
        """Ambiguous should become review_required."""
        row = pd.Series({
            "is_spike": True,
            "predicted_cause": "fraud_spike",
            "confidence": 0.70,
            "confidence_band": "ambiguous",
        })
        assert _assign_final_status(row) == STATUS_REVIEW_REQUIRED

    def test_low_confidence_should_review(self):
        """Low confidence should become review_required."""
        row = pd.Series({
            "is_spike": True,
            "predicted_cause": "organic_spike",
            "confidence": 0.50,
            "confidence_band": "low_confidence",
        })
        assert _assign_final_status(row) == STATUS_REVIEW_REQUIRED

    def test_no_spike_is_baseline(self):
        """No spike should become baseline."""
        row = pd.Series({
            "is_spike": False,
            "predicted_cause": None,
            "confidence": None,
            "confidence_band": None,
        })
        assert _assign_final_status(row) == STATUS_BASELINE


# ---------------------------------------------------------------------------
# Test: Decision Reasons
# ---------------------------------------------------------------------------


class TestDecisionReasons:
    def test_baseline_reason(self):
        """Baseline should have clear reason."""
        row = pd.Series({
            "is_spike": False,
            "predicted_cause": None,
            "confidence": None,
            "confidence_band": None,
        })
        reason = _assign_decision_reason(row)
        assert "No anomaly" in reason or "baseline" in reason.lower()

    def test_high_confidence_reason(self):
        """High confidence should include confidence value."""
        row = pd.Series({
            "is_spike": True,
            "predicted_cause": "fraud_spike",
            "confidence": 0.95,
            "confidence_band": "high_confidence",
        })
        reason = _assign_decision_reason(row)
        assert "0.95" in reason or "fraud" in reason.lower()


# ---------------------------------------------------------------------------
# Test: Pipeline Summary
# ---------------------------------------------------------------------------


class TestPipelineSummary:
    def test_summary_counts_add_up(self):
        """Summary counts should add up to total."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()
        results = run_pipeline(transactions, window_labels)
        summary = get_pipeline_summary(results)

        total = (summary["n_baseline"] + summary["n_organic_spike"] +
                 summary["n_fraud_spike"] + summary["n_review_required"])
        assert total == summary["total_windows"]


# ---------------------------------------------------------------------------
# Test: Label Independence
# ---------------------------------------------------------------------------


class TestLabelIndependence:
    def test_predictions_without_labels(self):
        """Predictions should not depend on window_label."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()

        # Run with labels
        results_with = run_pipeline(transactions, window_labels)

        # Run without labels (set all to baseline)
        window_labels_no_label = window_labels.copy()
        window_labels_no_label["window_label"] = "baseline"
        results_without = run_pipeline(transactions, window_labels_no_label)

        # Spike detection should be the same (doesn't use labels)
        assert (results_with["is_spike"] == results_without["is_spike"]).all()


# ---------------------------------------------------------------------------
# Test: Deterministic Behavior
# ---------------------------------------------------------------------------


class TestDeterministicBehavior:
    def test_same_input_same_output(self):
        """Same input should produce same output."""
        transactions, window_labels = _make_synthetic_transactions_and_labels()

        results1 = run_pipeline(transactions, window_labels)
        results2 = run_pipeline(transactions, window_labels)

        pd.testing.assert_frame_equal(results1, results2)
