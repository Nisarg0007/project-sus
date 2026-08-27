"""
Tests for investigation persistence.

Verifies that InvestigationService correctly persists InvestigationRun
and PersistedIncident records to the database after a successful pipeline run.

Uses in-memory SQLite and mocked pipeline to avoid needing real data files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base
from src.database.models import InvestigationRun, PersistedIncident
from src.domain.enums import (
    ConfidenceBand,
    IncidentSeverity,
    IncidentStatus,
    PipelineClassification,
)
from src.domain.models import Incident, PipelineSummary
from src.services.investigation_service import InvestigationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Create a database session for testing."""
    TestSession = sessionmaker(bind=db_engine)
    session = TestSession()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_pipeline_results() -> pd.DataFrame:
    """Create a fake pipeline results DataFrame for testing."""
    return pd.DataFrame(
        {
            "merchant_id": ["merchant_001", "merchant_002", "merchant_003"],
            "date": ["2025-07-24", "2025-07-25", "2025-07-26"],
            "transaction_count": [150, 200, 180],
            "volume_zscore_7d": [3.2, 1.5, 0.8],
            "is_spike": [True, True, False],
            "final_status": [
                "fraud_spike",
                "review_required",
                "baseline",
            ],
            "fraud_probability": [0.961, 0.72, 0.10],
            "confidence": [0.89, 0.65, 0.40],
            "confidence_band": [
                "high_confidence",
                "ambiguous",
                "low_confidence",
            ],
            "predicted_cause": ["payment_failure", None, None],
            "decision_reason": [
                "High fraud probability",
                "Ambiguous signals",
                "",
            ],
            "anomaly_summary": [
                "Payment failures increased",
                "Volume above normal",
                "",
            ],
            "top_fraud_signal": ["payment_failure_rate", "", ""],
            "volume_rolling_mean_7d": [100, 120, 170],
        }
    )


def _make_fake_summary() -> dict:
    """Create a fake pipeline summary dict."""
    return {
        "total_windows": 360,
        "n_baseline": 287,
        "n_organic_spike": 39,
        "n_fraud_spike": 31,
        "n_review_required": 3,
        "n_spikes_detected": 73,
        "spike_rate": 0.203,
    }


def _run_service_with_mock(db_session: Session, **service_kwargs) -> dict:
    """Run InvestigationService with mocked pipeline and real DB session."""
    service = InvestigationService()

    fake_results = _make_fake_pipeline_results()
    fake_summary = _make_fake_summary()

    with patch(
        "src.services.investigation_service.pd.read_csv",
        return_value=pd.DataFrame(),
    ), patch(
        "src.services.investigation_service.run_pipeline",
        return_value=fake_results,
    ), patch(
        "src.services.investigation_service.get_pipeline_summary",
        return_value=fake_summary,
    ):
        defaults = {
            "transactions_path": "data/raw/transactions.csv",
            "window_labels_path": "data/raw/window_labels.csv",
            "z_threshold": 0.5,
            "min_history_days": 3,
            "db": db_session,
        }
        defaults.update(service_kwargs)
        return service.run_investigation(**defaults)


# ===========================================================================
# Tests: Successful persistence
# ===========================================================================


class TestSuccessfulPersistence:
    """Tests that successful investigations are persisted correctly."""

    def test_persists_investigation_run(self, db_session):
        """Should create exactly one InvestigationRun record."""
        result = _run_service_with_mock(db_session)

        count = db_session.query(InvestigationRun).count()
        assert count == 1

    def test_persists_all_incidents(self, db_session):
        """Should persist incidents for fraud_spike and review_required only."""
        result = _run_service_with_mock(db_session)

        # Pipeline has 2 non-baseline rows: fraud_spike + review_required
        count = db_session.query(PersistedIncident).count()
        assert count == 2

    def test_investigation_id_matches(self, db_session):
        """Persisted investigation_id should match the service result."""
        result = _run_service_with_mock(db_session)

        run = db_session.query(InvestigationRun).first()
        assert run.investigation_id == result["investigation_id"]

    def test_summary_fields_correct(self, db_session):
        """Persisted summary fields should match the pipeline summary."""
        result = _run_service_with_mock(db_session)

        run = db_session.query(InvestigationRun).first()
        summary = result["summary"]

        assert run.total_results == result["total_results"]
        assert run.spikes_detected == summary.spikes_detected
        assert run.fraud_incidents == summary.fraud_incidents
        assert run.organic_incidents == summary.organic_incidents
        assert run.review_required == summary.review_required
        assert run.baseline_windows == summary.baseline_windows
        assert run.spike_rate == summary.spike_rate

    def test_input_parameters_persisted(self, db_session):
        """Input parameters should be stored in the InvestigationRun."""
        result = _run_service_with_mock(
            db_session,
            z_threshold=1.0,
            merchant_filter="merchant_001",
        )

        run = db_session.query(InvestigationRun).first()
        assert run.transactions_path == "data/raw/transactions.csv"
        assert run.window_labels_path == "data/raw/window_labels.csv"
        assert run.z_threshold == 1.0
        assert run.min_history_days == 3
        assert run.merchant_filter == "merchant_001"
        assert run.status == "completed"

    def test_incident_fields_correct(self, db_session):
        """Persisted incident fields should match domain incident values."""
        result = _run_service_with_mock(db_session)

        incidents = db_session.query(PersistedIncident).all()
        assert len(incidents) == 2

        # Find the fraud incident
        fraud_inc = next(
            i for i in incidents if i.classification == "fraud_spike"
        )
        assert fraud_inc.merchant_id == "merchant_001"
        assert fraud_inc.date == "2025-07-24"
        assert fraud_inc.severity == "critical"
        assert fraud_inc.fraud_probability == pytest.approx(0.961, abs=0.01)
        assert fraud_inc.confidence == pytest.approx(0.89, abs=0.01)
        assert fraud_inc.confidence_band == "high_confidence"
        assert fraud_inc.anomaly_score == pytest.approx(3.2, abs=0.1)

        # Find the review incident
        review_inc = next(
            i for i in incidents if i.classification == "review_required"
        )
        assert review_inc.merchant_id == "merchant_002"
        assert review_inc.severity in ("high", "medium", "low")

    def test_top_signals_serialized(self, db_session):
        """top_signals should be stored as JSON and deserializable."""
        result = _run_service_with_mock(db_session)

        incidents = db_session.query(PersistedIncident).all()
        for inc in incidents:
            parsed = json.loads(inc.top_signals_json)
            assert isinstance(parsed, list)
            assert all(isinstance(s, str) for s in parsed)

    def test_incidents_linked_to_run(self, db_session):
        """All persisted incidents should be linked to the correct run."""
        result = _run_service_with_mock(db_session)

        run = db_session.query(InvestigationRun).first()
        incidents = db_session.query(PersistedIncident).all()

        for inc in incidents:
            assert inc.investigation_run_id == run.id

    def test_created_at_set(self, db_session):
        """InvestigationRun should have created_at populated."""
        result = _run_service_with_mock(db_session)

        run = db_session.query(InvestigationRun).first()
        assert run.created_at is not None


# ===========================================================================
# Tests: Transaction behavior
# ===========================================================================


class TestTransactionBehavior:
    """Tests for commit/rollback behavior."""

    def test_committed_once_on_success(self, db_session):
        """On success, session.commit() should be called exactly once."""
        db_session.commit = MagicMock(wraps=db_session.commit)

        _run_service_with_mock(db_session)

        # commit() called once by the service
        assert db_session.commit.call_count == 1

    def test_no_commit_without_db(self, db_session):
        """When db=None, no database operations should occur."""
        service = InvestigationService()

        fake_results = _make_fake_pipeline_results()
        fake_summary = _make_fake_summary()

        with patch(
            "src.services.investigation_service.pd.read_csv",
            return_value=pd.DataFrame(),
        ), patch(
            "src.services.investigation_service.run_pipeline",
            return_value=fake_results,
        ), patch(
            "src.services.investigation_service.get_pipeline_summary",
            return_value=fake_summary,
        ):
            result = service.run_investigation(
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=0.5,
                min_history_days=3,
                db=None,
            )

        # No records should exist
        assert db_session.query(InvestigationRun).count() == 0
        assert db_session.query(PersistedIncident).count() == 0

    def test_persistence_failure_does_not_crash(self, db_session):
        """If persistence fails, the service should still return results."""
        service = InvestigationService()

        fake_results = _make_fake_pipeline_results()
        fake_summary = _make_fake_summary()

        with patch(
            "src.services.investigation_service.pd.read_csv",
            return_value=pd.DataFrame(),
        ), patch(
            "src.services.investigation_service.run_pipeline",
            return_value=fake_results,
        ), patch(
            "src.services.investigation_service.get_pipeline_summary",
            return_value=fake_summary,
        ), patch(
            "src.repositories.investigation_repository.InvestigationRepository.create_investigation",
            side_effect=Exception("DB connection lost"),
        ):
            # Should NOT raise — degraded mode
            result = service.run_investigation(
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=0.5,
                min_history_days=3,
                db=db_session,
            )

        # Results should still be returned
        assert "investigation_id" in result
        assert isinstance(result["summary"], PipelineSummary)

    def test_persistence_failure_rollback(self, db_session):
        """If persistence fails, session.rollback() should be called."""
        # First persist something to have data in the session
        run = InvestigationRun(
            investigation_id="INV-PREVIOUS",
            transactions_path="x",
            window_labels_path="y",
            z_threshold=0.5,
            min_history_days=3,
            total_results=10,
            spikes_detected=1,
            fraud_incidents=1,
            organic_incidents=0,
            review_required=0,
            baseline_windows=9,
            spike_rate=0.1,
        )
        db_session.add(run)
        db_session.commit()

        db_session.rollback = MagicMock(wraps=db_session.rollback)

        service = InvestigationService()
        fake_results = _make_fake_pipeline_results()
        fake_summary = _make_fake_summary()

        with patch(
            "src.services.investigation_service.pd.read_csv",
            return_value=pd.DataFrame(),
        ), patch(
            "src.services.investigation_service.run_pipeline",
            return_value=fake_results,
        ), patch(
            "src.services.investigation_service.get_pipeline_summary",
            return_value=fake_summary,
        ), patch(
            "src.repositories.investigation_repository.InvestigationRepository.create_investigation",
            side_effect=Exception("DB error"),
        ):
            result = service.run_investigation(
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=0.5,
                min_history_days=3,
                db=db_session,
            )

        # rollback should have been called
        assert db_session.rollback.call_count >= 1


# ===========================================================================
# Tests: API response unchanged
# ===========================================================================


class TestAPIResponseUnchanged:
    """Tests that the API response contract is preserved."""

    def test_response_shape_unchanged(self, db_session):
        """Response should have the same keys as before persistence was added."""
        result = _run_service_with_mock(db_session)

        assert "investigation_id" in result
        assert "summary" in result
        assert "incidents" in result
        assert "total_results" in result
        assert "processing_note" in result
        assert isinstance(result["summary"], PipelineSummary)
        assert isinstance(result["incidents"], list)

    def test_incident_domain_models_unchanged(self, db_session):
        """Incidents should still be Incident domain models."""
        result = _run_service_with_mock(db_session)

        for incident in result["incidents"]:
            assert isinstance(incident, Incident)
            assert incident.id.startswith("INC-")
            assert incident.severity in IncidentSeverity
            assert incident.classification in PipelineClassification

    def test_summary_values_unchanged(self, db_session):
        """Summary values should match the fake pipeline output."""
        result = _run_service_with_mock(db_session)

        summary = result["summary"]
        assert summary.total_windows == 360
        assert summary.spikes_detected == 73
        assert summary.spike_rate == 0.203
        assert summary.fraud_incidents == 31
        assert summary.organic_incidents == 39
        assert summary.review_required == 3
        assert summary.baseline_windows == 287

    def test_total_results_unchanged(self, db_session):
        """total_results should be the length of pipeline results."""
        result = _run_service_with_mock(db_session)

        assert result["total_results"] == 3
