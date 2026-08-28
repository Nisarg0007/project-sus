"""
Tests for InvestigationHistoryService.

Verifies:
- Paginated listing of investigations
- Detail retrieval with incidents
- top_signals JSON deserialization
- Empty database behavior
- Ordering and pagination
- Not-found handling
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import InvestigationRun, PersistedIncident
from src.repositories.investigation_repository import InvestigationRepository
from src.services.investigation_history_service import InvestigationHistoryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Create an isolated in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def service():
    return InvestigationHistoryService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_investigation(
    session,
    investigation_id: str = "INV-TEST001",
    **overrides,
) -> InvestigationRun:
    """Create and persist a test InvestigationRun."""
    defaults = dict(
        investigation_id=investigation_id,
        status="completed",
        transactions_path="data/raw/transactions.csv",
        window_labels_path="data/raw/window_labels.csv",
        model_path=None,
        z_threshold=2.0,
        min_history_days=3,
        merchant_filter=None,
        total_results=360,
        spikes_detected=73,
        fraud_incidents=31,
        organic_incidents=20,
        review_required=3,
        baseline_windows=287,
        spike_rate=0.203,
        processing_note="",
    )
    defaults.update(overrides)
    run = InvestigationRun(**defaults)
    session.add(run)
    session.flush()
    return run


def _create_incident(
    session,
    investigation_run_id: int,
    incident_id: str = "INC-TEST001",
    **overrides,
) -> PersistedIncident:
    """Create and persist a test PersistedIncident."""
    defaults = dict(
        investigation_run_id=investigation_run_id,
        incident_id=incident_id,
        merchant_id="merchant_001",
        date="2025-07-24",
        severity="critical",
        status="open",
        classification="fraud_spike",
        predicted_cause=None,
        fraud_probability=0.961,
        confidence=0.89,
        confidence_band="high_confidence",
        anomaly_score=3.8,
        decision_reason="Coordinated fraud pattern",
        anomaly_summary="Payment failure rate elevated",
        top_signals_json=json.dumps(["failed_payments: +157%", "ip_diversity: -42%"]),
        recommended_action="Review affected transactions",
    )
    defaults.update(overrides)
    inc = PersistedIncident(**defaults)
    session.add(inc)
    session.flush()
    return inc


# ---------------------------------------------------------------------------
# List Investigations
# ---------------------------------------------------------------------------


class TestListInvestigations:
    def test_empty_database(self, db_session, service):
        result = service.list_investigations(db_session)
        assert result.total == 0
        assert result.items == []
        assert result.limit == 20
        assert result.offset == 0

    def test_returns_investigations(self, db_session, service):
        _create_investigation(db_session, investigation_id="INV-001")
        _create_investigation(db_session, investigation_id="INV-002")
        db_session.commit()

        result = service.list_investigations(db_session)
        assert result.total == 2
        assert len(result.items) == 2

    def test_newest_first_ordering(self, db_session, service):
        _create_investigation(
            db_session, investigation_id="INV-OLD", processing_note="first"
        )
        _create_investigation(
            db_session, investigation_id="INV-NEW", processing_note="second"
        )
        db_session.commit()

        result = service.list_investigations(db_session)
        # Newest first — INV-NEW should be first
        assert result.items[0].investigation_id == "INV-NEW"
        assert result.items[1].investigation_id == "INV-OLD"

    def test_limit(self, db_session, service):
        for i in range(5):
            _create_investigation(db_session, investigation_id=f"INV-{i:03d}")
        db_session.commit()

        result = service.list_investigations(db_session, limit=2)
        assert len(result.items) == 2
        assert result.total == 5

    def test_offset(self, db_session, service):
        for i in range(5):
            _create_investigation(db_session, investigation_id=f"INV-{i:03d}")
        db_session.commit()

        result = service.list_investigations(db_session, limit=2, offset=2)
        assert len(result.items) == 2
        assert result.total == 5
        # Should skip the first 2 (newest)
        assert result.items[0].investigation_id == "INV-002"

    def test_offset_beyond_total(self, db_session, service):
        _create_investigation(db_session, investigation_id="INV-001")
        db_session.commit()

        result = service.list_investigations(db_session, offset=100)
        assert result.items == []
        assert result.total == 1

    def test_list_item_fields(self, db_session, service):
        _create_investigation(
            db_session,
            investigation_id="INV-FIELDS",
            total_results=100,
            spikes_detected=10,
            fraud_incidents=5,
            spike_rate=0.1,
        )
        db_session.commit()

        result = service.list_investigations(db_session)
        item = result.items[0]
        assert item.investigation_id == "INV-FIELDS"
        assert item.total_results == 100
        assert item.spikes_detected == 10
        assert item.fraud_incidents == 5
        assert item.spike_rate == 0.1
        assert item.status == "completed"


# ---------------------------------------------------------------------------
# Get Investigation Detail
# ---------------------------------------------------------------------------


class TestGetInvestigationDetail:
    def test_not_found(self, db_session, service):
        result = service.get_investigation_detail(db_session, "INV-NONEXISTENT")
        assert result is None

    def test_returns_detail(self, db_session, service):
        run = _create_investigation(
            db_session,
            investigation_id="INV-DETAIL",
            z_threshold=3.0,
            min_history_days=5,
            merchant_filter="merchant_003",
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-DETAIL")
        assert result is not None
        assert result.investigation_id == "INV-DETAIL"
        assert result.z_threshold == 3.0
        assert result.min_history_days == 5
        assert result.merchant_filter == "merchant_003"

    def test_includes_incidents(self, db_session, service):
        run = _create_investigation(db_session, investigation_id="INV-INC")
        _create_incident(
            db_session,
            investigation_run_id=run.id,
            incident_id="INC-001",
        )
        _create_incident(
            db_session,
            investigation_run_id=run.id,
            incident_id="INC-002",
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-INC")
        assert len(result.incidents) == 2
        ids = {inc.incident_id for inc in result.incidents}
        assert ids == {"INC-001", "INC-002"}

    def test_incidents_not_leaked(self, db_session, service):
        """Incidents from another investigation should not appear."""
        run1 = _create_investigation(db_session, investigation_id="INV-A")
        run2 = _create_investigation(db_session, investigation_id="INV-B")
        _create_incident(
            db_session,
            investigation_run_id=run1.id,
            incident_id="INC-A1",
        )
        _create_incident(
            db_session,
            investigation_run_id=run2.id,
            incident_id="INC-B1",
        )
        db_session.commit()

        result_a = service.get_investigation_detail(db_session, "INV-A")
        assert len(result_a.incidents) == 1
        assert result_a.incidents[0].incident_id == "INC-A1"

    def test_top_signals_deserialized(self, db_session, service):
        signals = ["failed_payments: +157%", "ip_diversity: -42%"]
        run = _create_investigation(db_session, investigation_id="INV-SIG")
        _create_incident(
            db_session,
            investigation_run_id=run.id,
            incident_id="INC-SIG",
            top_signals_json=json.dumps(signals),
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-SIG")
        inc = result.incidents[0]
        assert inc.top_signals == signals
        assert isinstance(inc.top_signals, list)

    def test_top_signals_invalid_json(self, db_session, service):
        run = _create_investigation(db_session, investigation_id="INV-BAD")
        _create_incident(
            db_session,
            investigation_run_id=run.id,
            incident_id="INC-BAD",
            top_signals_json="not valid json {{{",
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-BAD")
        assert result.incidents[0].top_signals == []

    def test_top_signals_empty_array(self, db_session, service):
        run = _create_investigation(db_session, investigation_id="INV-EMPTY")
        _create_incident(
            db_session,
            investigation_run_id=run.id,
            incident_id="INC-EMPTY",
            top_signals_json="[]",
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-EMPTY")
        assert result.incidents[0].top_signals == []

    def test_incident_fields_mapped(self, db_session, service):
        run = _create_investigation(db_session, investigation_id="INV-MAP")
        _create_incident(
            db_session,
            investigation_run_id=run.id,
            incident_id="INC-MAP",
            merchant_id="merchant_005",
            date="2025-08-01",
            severity="high",
            classification="organic_spike",
            fraud_probability=0.12,
            confidence=0.75,
            confidence_band="ambiguous",
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-MAP")
        inc = result.incidents[0]
        assert inc.merchant_id == "merchant_005"
        assert inc.date == "2025-08-01"
        assert inc.severity == "high"
        assert inc.classification == "organic_spike"
        assert inc.fraud_probability == 0.12
        assert inc.confidence == 0.75
        assert inc.confidence_band == "ambiguous"

    def test_no_incidents(self, db_session, service):
        _create_investigation(db_session, investigation_id="INV-NOINC")
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-NOINC")
        assert result.incidents == []

    def test_summary_fields(self, db_session, service):
        _create_investigation(
            db_session,
            investigation_id="INV-SUM",
            total_results=500,
            spikes_detected=50,
            fraud_incidents=15,
            organic_incidents=25,
            review_required=10,
            baseline_windows=450,
            spike_rate=0.1,
            processing_note="Test note",
        )
        db_session.commit()

        result = service.get_investigation_detail(db_session, "INV-SUM")
        s = result.summary
        assert s.total_results == 500
        assert s.spikes_detected == 50
        assert s.fraud_incidents == 15
        assert s.organic_incidents == 25
        assert s.review_required == 10
        assert s.baseline_windows == 450
        assert s.spike_rate == 0.1
        assert s.processing_note == "Test note"
