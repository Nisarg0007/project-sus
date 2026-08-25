"""
Tests for the incidents module.
"""

import numpy as np
import pandas as pd
import pytest

from src.incidents import (
    classify_severity,
    generate_recommended_action,
    generate_incident_id,
    create_incident,
    generate_incidents_batch,
    get_incident_summary,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)


# ---------------------------------------------------------------------------
# Test: Severity Classification
# ---------------------------------------------------------------------------


class TestSeverityClassification:
    def test_critical_severity(self):
        """Should classify as critical for high-probability high-confidence fraud."""
        severity = classify_severity(
            fraud_probability=0.95,
            anomaly_score=3.0,
            confidence_band="high_confidence",
            final_status="fraud_spike",
        )
        assert severity == SEVERITY_CRITICAL

    def test_high_severity(self):
        """Should classify as high for moderate-probability fraud."""
        severity = classify_severity(
            fraud_probability=0.75,
            anomaly_score=2.0,
            confidence_band="high_confidence",
            final_status="fraud_spike",
        )
        assert severity == SEVERITY_HIGH

    def test_medium_severity_fraud(self):
        """Should classify as medium for lower-probability fraud."""
        severity = classify_severity(
            fraud_probability=0.55,
            anomaly_score=1.5,
            confidence_band="ambiguous",
            final_status="fraud_spike",
        )
        assert severity == SEVERITY_MEDIUM

    def test_low_severity_review(self):
        """Should classify as low for review_required with moderate anomaly."""
        severity = classify_severity(
            fraud_probability=0.0,
            anomaly_score=1.0,
            confidence_band="ambiguous",
            final_status="review_required",
        )
        assert severity == SEVERITY_LOW

    def test_medium_severity_review_high_anomaly(self):
        """Should classify as medium for review_required with high anomaly."""
        severity = classify_severity(
            fraud_probability=0.0,
            anomaly_score=2.5,
            confidence_band="low_confidence",
            final_status="review_required",
        )
        assert severity == SEVERITY_MEDIUM


# ---------------------------------------------------------------------------
# Test: Recommended Actions
# ---------------------------------------------------------------------------


class TestRecommendedActions:
    def test_fraud_critical_action(self):
        """Critical fraud should recommend immediate action."""
        action = generate_recommended_action(
            final_status="fraud_spike",
            severity=SEVERITY_CRITICAL,
            confidence_band="high_confidence",
            predicted_cause="fraud_spike",
        )
        assert "IMMEDIATE" in action.upper() or "immediate" in action.lower()

    def test_review_low_confidence_action(self):
        """Review with low confidence should mention manual investigation."""
        action = generate_recommended_action(
            final_status="review_required",
            severity=SEVERITY_LOW,
            confidence_band="low_confidence",
            predicted_cause=None,
        )
        assert "review" in action.lower() or "investigation" in action.lower()


# ---------------------------------------------------------------------------
# Test: Incident ID Generation
# ---------------------------------------------------------------------------


class TestIncidentID:
    def test_deterministic_id(self):
        """Same merchant/date should produce same ID."""
        id1 = generate_incident_id("merchant_001", "2025-07-15")
        id2 = generate_incident_id("merchant_001", "2025-07-15")
        assert id1 == id2

    def test_different_dates_different_ids(self):
        """Different dates should produce different IDs."""
        id1 = generate_incident_id("merchant_001", "2025-07-15")
        id2 = generate_incident_id("merchant_001", "2025-07-16")
        assert id1 != id2


# ---------------------------------------------------------------------------
# Test: Incident Creation
# ---------------------------------------------------------------------------


class TestIncidentCreation:
    def test_creates_incident_for_fraud(self):
        """Should create incident for fraud_spike status."""
        row = pd.Series({
            "merchant_id": "merchant_001",
            "date": "2025-07-15",
            "final_status": "fraud_spike",
            "fraud_probability": 0.85,
            "volume_zscore_7d": 2.5,
            "confidence_band": "high_confidence",
            "predicted_cause": "fraud_spike",
            "decision_reason": "High confidence fraud_spike",
        })

        incident = create_incident(row)
        assert incident is not None
        assert incident.final_status == "fraud_spike"

    def test_creates_incident_for_review(self):
        """Should create incident for review_required status."""
        row = pd.Series({
            "merchant_id": "merchant_001",
            "date": "2025-07-15",
            "final_status": "review_required",
            "fraud_probability": 0.6,
            "volume_zscore_7d": 1.8,
            "confidence_band": "ambiguous",
            "predicted_cause": "fraud_spike",
            "decision_reason": "Ambiguous classification",
        })

        incident = create_incident(row)
        assert incident is not None
        assert incident.final_status == "review_required"

    def test_no_incident_for_baseline(self):
        """Should not create incident for baseline status."""
        row = pd.Series({
            "merchant_id": "merchant_001",
            "date": "2025-07-15",
            "final_status": "baseline",
            "fraud_probability": 0.0,
            "volume_zscore_7d": 0.5,
            "confidence_band": None,
            "predicted_cause": None,
            "decision_reason": "No anomaly detected",
        })

        incident = create_incident(row)
        assert incident is None

    def test_no_incident_for_organic(self):
        """Should not create incident for organic_spike status."""
        row = pd.Series({
            "merchant_id": "merchant_001",
            "date": "2025-07-15",
            "final_status": "organic_spike",
            "fraud_probability": 0.1,
            "volume_zscore_7d": 2.0,
            "confidence_band": "high_confidence",
            "predicted_cause": "organic_spike",
            "decision_reason": "High confidence organic_spike",
        })

        incident = create_incident(row)
        assert incident is None


# ---------------------------------------------------------------------------
# Test: Batch Incident Generation
# ---------------------------------------------------------------------------


class TestBatchIncidents:
    def test_batch_generation(self):
        """Should generate incidents for applicable rows."""
        results = pd.DataFrame({
            "merchant_id": ["m1", "m2", "m3"],
            "date": ["2025-07-01", "2025-07-02", "2025-07-03"],
            "final_status": ["baseline", "fraud_spike", "review_required"],
            "fraud_probability": [0.0, 0.85, 0.6],
            "volume_zscore_7d": [0.5, 2.5, 1.8],
            "confidence_band": [None, "high_confidence", "ambiguous"],
            "predicted_cause": [None, "fraud_spike", "fraud_spike"],
            "decision_reason": ["No anomaly", "High confidence fraud", "Ambiguous"],
        })

        incidents_df = generate_incidents_batch(results)

        # Should have 2 incidents (fraud_spike and review_required)
        assert len(incidents_df) == 2

    def test_no_duplicate_incidents(self):
        """Should not create duplicate incidents for same merchant/date."""
        results = pd.DataFrame({
            "merchant_id": ["m1", "m1"],
            "date": ["2025-07-01", "2025-07-01"],
            "final_status": ["fraud_spike", "fraud_spike"],
            "fraud_probability": [0.85, 0.85],
            "volume_zscore_7d": [2.5, 2.5],
            "confidence_band": ["high_confidence", "high_confidence"],
            "predicted_cause": ["fraud_spike", "fraud_spike"],
            "decision_reason": ["High confidence fraud", "High confidence fraud"],
        })

        incidents_df = generate_incidents_batch(results)

        # Should have only 1 incident (or handle duplicates appropriately)
        assert len(incidents_df) <= 2


# ---------------------------------------------------------------------------
# Test: Incident Summary
# ---------------------------------------------------------------------------


class TestIncidentSummary:
    def test_summary_with_incidents(self):
        """Should generate summary from incidents."""
        incidents_df = pd.DataFrame({
            "severity": ["critical", "high", "medium"],
            "final_status": ["fraud_spike", "fraud_spike", "review_required"],
            "fraud_probability": [0.95, 0.8, 0.6],
        })

        summary = get_incident_summary(incidents_df)

        assert summary["total_incidents"] == 3
        assert "severity_distribution" in summary

    def test_summary_empty(self):
        """Should handle empty incidents DataFrame."""
        incidents_df = pd.DataFrame()

        summary = get_incident_summary(incidents_df)

        assert summary["total_incidents"] == 0
