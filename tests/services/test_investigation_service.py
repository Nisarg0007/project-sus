"""
Tests for the InvestigationService.

These tests verify the service correctly orchestrates the pipeline,
converts results to domain models, and handles edge cases.
"""

import pytest

from src.domain.enums import (
    ConfidenceBand,
    IncidentSeverity,
    IncidentStatus,
    InvestigationStatus,
    PipelineClassification,
)
from src.domain.models import (
    Incident,
    Investigation,
    Merchant,
    PipelineSummary,
    BehavioralEvidence,
)
from src.services.investigation_service import (
    InvestigationService,
    _map_classification,
    _map_confidence_band,
    _map_severity,
    _safe_float,
    _safe_str,
)


# ---------------------------------------------------------------------------
# Test: Domain Enum Mapping
# ---------------------------------------------------------------------------


class TestEnumMapping:
    """Tests for internal enum mapping helpers."""

    def test_map_classification_baseline(self):
        assert _map_classification("baseline") == PipelineClassification.BASELINE

    def test_map_classification_fraud(self):
        assert _map_classification("fraud_spike") == PipelineClassification.FRAUD_SPIKE

    def test_map_classification_organic(self):
        assert _map_classification("organic_spike") == PipelineClassification.ORGANIC_SPIKE

    def test_map_classification_review(self):
        assert _map_classification("review_required") == PipelineClassification.REVIEW_REQUIRED

    def test_map_classification_unknown_defaults_review(self):
        assert _map_classification("unknown") == PipelineClassification.REVIEW_REQUIRED

    def test_map_severity_critical(self):
        assert _map_severity("critical") == IncidentSeverity.CRITICAL

    def test_map_severity_high(self):
        assert _map_severity("high") == IncidentSeverity.HIGH

    def test_map_severity_unknown_defaults_low(self):
        assert _map_severity("unknown") == IncidentSeverity.LOW

    def test_map_confidence_band_high(self):
        assert _map_confidence_band("high_confidence") == ConfidenceBand.HIGH_CONFIDENCE

    def test_map_confidence_band_none(self):
        assert _map_confidence_band(None) == ConfidenceBand.LOW_CONFIDENCE


# ---------------------------------------------------------------------------
# Test: Safe Type Conversion
# ---------------------------------------------------------------------------


class TestSafeConversion:
    """Tests for NaN-safe type conversion helpers."""

    def test_safe_float_normal(self):
        assert _safe_float(3.14) == 3.14

    def test_safe_float_nan(self):
        import numpy as np
        assert _safe_float(np.nan) == 0.0

    def test_safe_float_nan_with_default(self):
        import numpy as np
        assert _safe_float(np.nan, -1.0) == -1.0

    def test_safe_str_normal(self):
        assert _safe_str("hello") == "hello"

    def test_safe_str_nan(self):
        import numpy as np
        assert _safe_str(np.nan) == ""

    def test_safe_str_nan_with_default(self):
        import numpy as np
        assert _safe_str(np.nan, "default") == "default"


# ---------------------------------------------------------------------------
# Test: Domain Model Creation
# ---------------------------------------------------------------------------


class TestDomainModels:
    """Tests for domain model construction."""

    def test_merchant_creation(self):
        merchant = Merchant(
            id="merchant_001",
            name="Test Merchant",
            daily_volume=500,
            risk_level="low",
        )
        assert merchant.id == "merchant_001"
        assert merchant.daily_volume == 500

    def test_incident_creation(self):
        incident = Incident(
            id="INC-merchant_001-20250724",
            merchant_id="merchant_001",
            date="2025-07-24",
            severity=IncidentSeverity.CRITICAL,
            classification=PipelineClassification.FRAUD_SPIKE,
            fraud_probability=0.961,
            confidence=0.961,
            confidence_band=ConfidenceBand.HIGH_CONFIDENCE,
            anomaly_score=3.2,
        )
        assert incident.severity == IncidentSeverity.CRITICAL
        assert incident.fraud_probability == 0.961
        assert incident.status == IncidentStatus.OPEN  # default

    def test_investigation_creation(self):
        investigation = Investigation(
            id="INV-001",
            title="Test Investigation",
        )
        assert investigation.status == InvestigationStatus.INITIATED
        assert investigation.incidents == []

    def test_pipeline_summary_creation(self):
        summary = PipelineSummary(
            total_windows=360,
            spikes_detected=73,
            spike_rate=0.203,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
        )
        assert summary.total_windows == 360
        assert summary.spikes_detected == 73

    def test_behavioral_evidence_creation(self):
        evidence = BehavioralEvidence(
            feature="failed_payment_rate",
            label="Failed Payment Rate",
            normal_value=0.03,
            current_value=0.15,
            change_percent=157.0,
            signal_type="fraud",
        )
        assert evidence.feature == "failed_payment_rate"
        assert evidence.change_percent == 157.0


# ---------------------------------------------------------------------------
# Test: Investigation Service
# ---------------------------------------------------------------------------


class TestInvestigationService:
    """Tests for the InvestigationService (integration with pipeline)."""

    def test_service_instantiation(self):
        """Service should instantiate without errors."""
        service = InvestigationService()
        assert service is not None

    def test_get_status(self):
        """Status check should return expected fields."""
        service = InvestigationService()
        status = service.get_investigation_status()
        assert "app_name" in status
        assert "app_version" in status
        assert "pipeline_ready" in status

    def test_run_investigation_with_real_data(self):
        """Full pipeline integration test with generated data.

        This test verifies the entire flow:
        1. Load CSV data
        2. Run pipeline
        3. Convert to domain models
        4. Return structured result
        """
        import os

        # Skip if data files don't exist
        if not os.path.exists("data/raw/transactions.csv"):
            pytest.skip("Test data not generated. Run: python -m src.generate_data")

        service = InvestigationService()
        result = service.run_investigation()

        # Verify structure
        assert "investigation_id" in result
        assert result["investigation_id"].startswith("INV-")
        assert isinstance(result["summary"], PipelineSummary)
        assert isinstance(result["incidents"], list)
        assert isinstance(result["total_results"], int)
        assert result["total_results"] > 0

        # Verify summary consistency
        summary = result["summary"]
        total_from_summary = (
            summary.baseline_windows
            + summary.fraud_incidents
            + summary.organic_incidents
            + summary.review_required
        )
        assert total_from_summary == result["total_results"]

        # If there are incidents, verify their structure
        for incident in result["incidents"]:
            assert isinstance(incident, Incident)
            assert incident.id.startswith("INC-")
            assert incident.severity in IncidentSeverity
            assert incident.classification in PipelineClassification
            assert 0.0 <= incident.fraud_probability <= 1.0

    def test_run_investigation_with_merchant_filter(self):
        """Filtered investigation should return only matching merchant."""
        import os

        if not os.path.exists("data/raw/transactions.csv"):
            pytest.skip("Test data not generated.")

        service = InvestigationService()
        result = service.run_investigation(merchant_filter="merchant_001")

        for incident in result["incidents"]:
            assert incident.merchant_id == "merchant_001"

    def test_run_investigation_nonexistent_merchant(self):
        """Filtering to a non-existent merchant should return empty results."""
        import os

        if not os.path.exists("data/raw/transactions.csv"):
            pytest.skip("Test data not generated.")

        service = InvestigationService()
        result = service.run_investigation(merchant_filter="nonexistent_merchant")

        assert result["total_results"] == 0
        assert result["incidents"] == []
        assert "nonexistent" in result["processing_note"]

    def test_run_investigation_missing_data(self):
        """Missing data files should raise FileNotFoundError."""
        service = InvestigationService()
        with pytest.raises(FileNotFoundError):
            service.run_investigation(
                transactions_path="nonexistent_transactions.csv",
                window_labels_path="nonexistent_labels.csv",
            )
