"""
Tests for InvestigationRepository.

Verifies:
- Creating investigations
- Fetching by investigation_id
- Missing investigation returns None
- Listing investigations
- Limit behavior
- Newest-first ordering
- Creating incidents
- Fetching incidents for an investigation
- Multiple incidents under one investigation
- Empty incident result
- Repository methods do not commit unexpectedly
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base
from src.database.models import InvestigationRun, PersistedIncident
from src.repositories.investigation_repository import InvestigationRepository


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


@pytest.fixture()
def repo(db_session):
    """Create an InvestigationRepository bound to the test session."""
    return InvestigationRepository(db_session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_DEFAULTS = {
    "investigation_id": "INV-TEST00000001",
    "status": "completed",
    "transactions_path": "data/raw/transactions.csv",
    "window_labels_path": "data/raw/window_labels.csv",
    "model_path": None,
    "z_threshold": 0.5,
    "min_history_days": 3,
    "merchant_filter": None,
    "total_results": 360,
    "spikes_detected": 73,
    "fraud_incidents": 31,
    "organic_incidents": 39,
    "review_required": 3,
    "baseline_windows": 287,
    "spike_rate": 0.203,
    "processing_note": "",
}

_INCIDENT_DEFAULTS = {
    "incident_id": "INC-merchant_001-20250724",
    "merchant_id": "merchant_001",
    "date": "2025-07-24",
    "severity": "critical",
    "status": "open",
    "classification": "fraud_spike",
    "predicted_cause": "payment_failure",
    "fraud_probability": 0.961,
    "confidence": 0.89,
    "confidence_band": "high_confidence",
    "anomaly_score": 3.2,
    "decision_reason": "High fraud probability",
    "anomaly_summary": "Payment failures increased",
    "top_signals_json": json.dumps(["payment_failure_rate"]),
    "recommended_action": "Review affected transactions",
}


def _create_run(db_session: Session, **overrides) -> InvestigationRun:
    """Helper: create and commit an InvestigationRun directly."""
    data = {**_RUN_DEFAULTS, **overrides}
    run = InvestigationRun(**data)
    db_session.add(run)
    db_session.commit()
    return run


def _create_incident(db_session: Session, run_id: int, **overrides) -> PersistedIncident:
    """Helper: create and commit a PersistedIncident directly."""
    data = {**_INCIDENT_DEFAULTS, "investigation_run_id": run_id, **overrides}
    incident = PersistedIncident(**data)
    db_session.add(incident)
    db_session.commit()
    return incident


# ===========================================================================
# Tests: create_investigation
# ===========================================================================


class TestCreateInvestigation:
    """Tests for InvestigationRepository.create_investigation."""

    def test_create_and_retrieve(self, db_session, repo):
        """Should create an InvestigationRun and retrieve it by ID."""
        run = repo.create_investigation(
            investigation_id="INV-REPO00000001",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.commit()

        retrieved = repo.get_by_investigation_id("INV-REPO00000001")
        assert retrieved is not None
        assert retrieved.investigation_id == "INV-REPO00000001"
        assert retrieved.status == "completed"
        assert retrieved.total_results == 360
        assert retrieved.z_threshold == 0.5

    def test_create_sets_auto_id(self, db_session, repo):
        """The auto-generated id should be populated after flush."""
        run = repo.create_investigation(
            investigation_id="INV-REPO00000002",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=100,
            spikes_detected=10,
            fraud_incidents=5,
            organic_incidents=3,
            review_required=2,
            baseline_windows=90,
            spike_rate=0.1,
        )
        # After flush, id should be populated even before commit
        assert run.id is not None
        assert isinstance(run.id, int)

    def test_create_with_optional_fields(self, db_session, repo):
        """Optional fields like model_path and merchant_filter should work."""
        run = repo.create_investigation(
            investigation_id="INV-REPO00000003",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            model_path="models/custom.pkl",
            z_threshold=1.0,
            min_history_days=5,
            merchant_filter="merchant_001",
            total_results=50,
            spikes_detected=5,
            fraud_incidents=2,
            organic_incidents=2,
            review_required=1,
            baseline_windows=45,
            spike_rate=0.1,
            processing_note="Filtered to merchant_001",
        )
        db_session.commit()

        retrieved = repo.get_by_investigation_id("INV-REPO00000003")
        assert retrieved is not None
        assert retrieved.model_path == "models/custom.pkl"
        assert retrieved.merchant_filter == "merchant_001"
        assert retrieved.processing_note == "Filtered to merchant_001"

    def test_does_not_commit(self, db_session, repo):
        """create_investigation should flush but NOT commit."""
        run = repo.create_investigation(
            investigation_id="INV-REPO00000004",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=100,
            spikes_detected=10,
            fraud_incidents=5,
            organic_incidents=3,
            review_required=2,
            baseline_windows=90,
            spike_rate=0.1,
        )
        # id is populated (flushed) but session is not committed
        assert run.id is not None
        # Roll back to verify it's not persisted
        db_session.rollback()
        result = repo.get_by_investigation_id("INV-REPO00000004")
        assert result is None


# ===========================================================================
# Tests: get_by_investigation_id
# ===========================================================================


class TestGetByInvestigationId:
    """Tests for InvestigationRepository.get_by_investigation_id."""

    def test_found(self, db_session, repo):
        """Should return the InvestigationRun when found."""
        _create_run(db_session, investigation_id="INV-GET00000001")
        result = repo.get_by_investigation_id("INV-GET00000001")
        assert result is not None
        assert result.investigation_id == "INV-GET00000001"

    def test_not_found(self, db_session, repo):
        """Should return None when investigation_id does not exist."""
        result = repo.get_by_investigation_id("INV-NONEXISTENT")
        assert result is None

    def test_includes_incidents(self, db_session, repo):
        """Should eagerly load associated incidents."""
        run = _create_run(db_session, investigation_id="INV-GET00000002")
        _create_incident(db_session, run.id, incident_id="INC-001")
        _create_incident(db_session, run.id, incident_id="INC-002")

        retrieved = repo.get_by_investigation_id("INV-GET00000002")
        assert len(retrieved.incidents) == 2
        incident_ids = {i.incident_id for i in retrieved.incidents}
        assert incident_ids == {"INC-001", "INC-002"}

    def test_empty_incidents_list(self, db_session, repo):
        """Investigation with no incidents should return empty list."""
        _create_run(db_session, investigation_id="INV-GET00000003")
        retrieved = repo.get_by_investigation_id("INV-GET00000003")
        assert retrieved.incidents == []


# ===========================================================================
# Tests: list_investigations
# ===========================================================================


class TestListInvestigations:
    """Tests for InvestigationRepository.list_investigations."""

    def test_empty_database(self, db_session, repo):
        """Empty database should return an empty list."""
        result = repo.list_investigations()
        assert result == []

    def test_returns_all(self, db_session, repo):
        """Should return all investigations when no limit is set."""
        _create_run(db_session, investigation_id="INV-LIST0000001")
        _create_run(db_session, investigation_id="INV-LIST0000002")
        _create_run(db_session, investigation_id="INV-LIST0000003")

        result = repo.list_investigations()
        assert len(result) == 3

    def test_limit(self, db_session, repo):
        """Should respect the limit parameter."""
        for i in range(5):
            _create_run(
                db_session,
                investigation_id=f"INV-LIMIT00000{i}",
            )

        result = repo.list_investigations(limit=3)
        assert len(result) == 3

    def test_limit_larger_than_count(self, db_session, repo):
        """Limit larger than total should return all."""
        _create_run(db_session, investigation_id="INV-LIMT0000001")
        _create_run(db_session, investigation_id="INV-LIMT0000002")

        result = repo.list_investigations(limit=100)
        assert len(result) == 2

    def test_offset(self, db_session, repo):
        """Should skip the first N results."""
        for i in range(4):
            _create_run(
                db_session,
                investigation_id=f"INV-OFFS00000{i}",
            )

        all_runs = repo.list_investigations(limit=10)
        assert len(all_runs) == 4

        offset_runs = repo.list_investigations(limit=10, offset=2)
        assert len(offset_runs) == 2
        # The offset runs should be the last two (oldest), since ordering is newest first
        assert offset_runs[0].investigation_id == "INV-OFFS000001"
        assert offset_runs[1].investigation_id == "INV-OFFS000000"

    def test_newest_first_ordering(self, db_session, repo):
        """Investigations should be ordered by created_at DESC."""
        # Create runs with distinct timestamps
        run1 = _create_run(
            db_session, investigation_id="INV-ORDR000001"
        )
        run1.created_at = datetime(2025, 7, 1, tzinfo=timezone.utc)
        db_session.commit()

        run2 = _create_run(
            db_session, investigation_id="INV-ORDR000002"
        )
        run2.created_at = datetime(2025, 7, 3, tzinfo=timezone.utc)
        db_session.commit()

        run3 = _create_run(
            db_session, investigation_id="INV-ORDR000003"
        )
        run3.created_at = datetime(2025, 7, 2, tzinfo=timezone.utc)
        db_session.commit()

        result = repo.list_investigations()
        ids = [r.investigation_id for r in result]
        assert ids == [
            "INV-ORDR000002",  # Jul 3 (newest)
            "INV-ORDR000003",  # Jul 2
            "INV-ORDR000001",  # Jul 1 (oldest)
        ]

    def test_includes_incidents_via_selectin(self, db_session, repo):
        """Listed investigations should have incidents loaded."""
        run = _create_run(
            db_session, investigation_id="INV-LIST0000004"
        )
        _create_incident(db_session, run.id, incident_id="INC-LIST-001")

        result = repo.list_investigations(limit=10)
        assert len(result) == 1
        assert len(result[0].incidents) == 1
        assert result[0].incidents[0].incident_id == "INC-LIST-001"


# ===========================================================================
# Tests: count_investigations
# ===========================================================================


class TestCountInvestigations:
    """Tests for InvestigationRepository.count_investigations."""

    def test_empty(self, db_session, repo):
        """Empty database should return 0."""
        assert repo.count_investigations() == 0

    def test_counts_all(self, db_session, repo):
        """Should count all investigation runs."""
        _create_run(db_session, investigation_id="INV-CNT0000001")
        _create_run(db_session, investigation_id="INV-CNT0000002")
        assert repo.count_investigations() == 2


# ===========================================================================
# Tests: create_incident
# ===========================================================================


class TestCreateIncident:
    """Tests for InvestigationRepository.create_incident."""

    def test_create_and_retrieve(self, db_session, repo):
        """Should create an incident linked to a run."""
        run = _create_run(db_session, investigation_id="INV-INCD000001")

        incident = repo.create_incident(
            investigation_run_id=run.id,
            incident_id="INC-INCD001",
            merchant_id="merchant_001",
            date="2025-07-24",
            severity="critical",
            classification="fraud_spike",
            fraud_probability=0.961,
            confidence=0.89,
            confidence_band="high_confidence",
            anomaly_score=3.2,
        )
        db_session.commit()

        retrieved = db_session.query(PersistedIncident).filter_by(
            incident_id="INC-INCD001"
        ).first()
        assert retrieved is not None
        assert retrieved.merchant_id == "merchant_001"
        assert retrieved.fraud_probability == 0.961
        assert retrieved.investigation_run_id == run.id

    def test_create_sets_auto_id(self, db_session, repo):
        """The auto-generated id should be populated after flush."""
        run = _create_run(db_session, investigation_id="INV-INCD000002")

        incident = repo.create_incident(
            investigation_run_id=run.id,
            incident_id="INC-INCD002",
            merchant_id="merchant_001",
            date="2025-07-24",
            severity="high",
            classification="review_required",
            fraud_probability=0.65,
            confidence=0.70,
            confidence_band="ambiguous",
            anomaly_score=2.1,
        )
        assert incident.id is not None
        assert isinstance(incident.id, int)

    def test_does_not_commit(self, db_session, repo):
        """create_incident should flush but NOT commit."""
        run = _create_run(db_session, investigation_id="INV-INCD000003")

        repo.create_incident(
            investigation_run_id=run.id,
            incident_id="INC-INCD003",
            merchant_id="merchant_002",
            date="2025-07-25",
            severity="medium",
            classification="organic_spike",
            fraud_probability=0.10,
            confidence=0.60,
            confidence_band="low_confidence",
            anomaly_score=1.5,
        )
        db_session.rollback()
        count = db_session.query(PersistedIncident).count()
        assert count == 0

    def test_optional_fields(self, db_session, repo):
        """Nullable fields should work correctly."""
        run = _create_run(db_session, investigation_id="INV-INCD000004")

        incident = repo.create_incident(
            investigation_run_id=run.id,
            incident_id="INC-INCD004",
            merchant_id="merchant_003",
            date="2025-07-26",
            severity="low",
            classification="organic_spike",
            predicted_cause=None,
            fraud_probability=0.05,
            confidence=0.40,
            confidence_band="low_confidence",
            anomaly_score=0.8,
        )
        db_session.commit()

        retrieved = db_session.query(PersistedIncident).filter_by(
            incident_id="INC-INCD004"
        ).first()
        assert retrieved.predicted_cause is None


# ===========================================================================
# Tests: get_incidents_for_investigation
# ===========================================================================


class TestGetIncidentsForInvestigation:
    """Tests for InvestigationRepository.get_incidents_for_investigation."""

    def test_returns_incidents(self, db_session, repo):
        """Should return all incidents for an investigation."""
        run = _create_run(db_session, investigation_id="INV-GINC000001")
        _create_incident(db_session, run.id, incident_id="INC-GI-001")
        _create_incident(db_session, run.id, incident_id="INC-GI-002")
        _create_incident(db_session, run.id, incident_id="INC-GI-003")

        incidents = repo.get_incidents_for_investigation("INV-GINC000001")
        assert len(incidents) == 3
        ids = {i.incident_id for i in incidents}
        assert ids == {"INC-GI-001", "INC-GI-002", "INC-GI-003"}

    def test_empty_when_no_incidents(self, db_session, repo):
        """Investigation with no incidents should return empty list."""
        _create_run(db_session, investigation_id="INV-GINC000002")
        incidents = repo.get_incidents_for_investigation("INV-GINC000002")
        assert incidents == []

    def test_empty_when_investigation_not_found(self, db_session, repo):
        """Non-existent investigation should return empty list."""
        incidents = repo.get_incidents_for_investigation("INV-NONEXISTENT")
        assert incidents == []

    def test_only_returns_own_incidents(self, db_session, repo):
        """Should not return incidents from other investigations."""
        run1 = _create_run(db_session, investigation_id="INV-GINC000003")
        run2 = _create_run(db_session, investigation_id="INV-GINC000004")

        _create_incident(db_session, run1.id, incident_id="INC-OWN-001")
        _create_incident(db_session, run2.id, incident_id="INC-OTHER-001")

        incidents = repo.get_incidents_for_investigation("INV-GINC000003")
        assert len(incidents) == 1
        assert incidents[0].incident_id == "INC-OWN-001"


# ===========================================================================
# Tests: Multiple incidents + combined operations
# ===========================================================================


class TestCombinedOperations:
    """Tests for realistic combined repository usage patterns."""

    def test_create_run_then_incidents(self, db_session, repo):
        """Create a run, add incidents, retrieve with incidents."""
        run = repo.create_investigation(
            investigation_id="INV-COMB000001",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )

        repo.create_incident(
            investigation_run_id=run.id,
            incident_id="INC-COMB-001",
            merchant_id="merchant_001",
            date="2025-07-24",
            severity="critical",
            classification="fraud_spike",
            fraud_probability=0.961,
            confidence=0.89,
            confidence_band="high_confidence",
            anomaly_score=3.2,
        )
        repo.create_incident(
            investigation_run_id=run.id,
            incident_id="INC-COMB-002",
            merchant_id="merchant_002",
            date="2025-07-25",
            severity="high",
            classification="review_required",
            fraud_probability=0.72,
            confidence=0.65,
            confidence_band="ambiguous",
            anomaly_score=2.4,
        )
        db_session.commit()

        # Retrieve via get_by_investigation_id
        retrieved = repo.get_by_investigation_id("INV-COMB000001")
        assert retrieved is not None
        assert len(retrieved.incidents) == 2

        # Retrieve via get_incidents_for_investigation
        incidents = repo.get_incidents_for_investigation("INV-COMB000001")
        assert len(incidents) == 2

        # Count
        assert repo.count_investigations() == 1

    def test_list_with_incidents(self, db_session, repo):
        """Multiple runs with different incident counts should list correctly."""
        run1 = _create_run(
            db_session, investigation_id="INV-CMBL000001"
        )
        run2 = _create_run(
            db_session, investigation_id="INV-CMBL000002"
        )

        _create_incident(db_session, run1.id, incident_id="INC-CMBL-001")
        _create_incident(db_session, run1.id, incident_id="INC-CMBL-002")
        _create_incident(db_session, run2.id, incident_id="INC-CMBL-003")

        runs = repo.list_investigations()
        assert len(runs) == 2

        # Find by ID and verify incident counts
        for run in runs:
            if run.investigation_id == "INV-CMBL000001":
                assert len(run.incidents) == 2
            elif run.investigation_id == "INV-CMBL000002":
                assert len(run.incidents) == 1
