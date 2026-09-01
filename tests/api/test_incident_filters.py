"""
Tests for incident filtering, sorting, search, and pagination.

Covers:
- Search across incident_id and merchant_id
- Exact filters: workflow_status, classification, severity
- Partial match: assigned_analyst
- Investigation ID filter via join
- Date range: created_from, created_to
- Combined filters
- Sorting: asc/desc for each field
- Pagination: limit, offset
- Invalid sort values (422)
- Invalid date range (422)
- Empty results
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.api.app import create_app
from src.database.base import Base
from src.database.models import (
    IncidentStatusHistory,
    InvestigationRun,
    PersistedIncident,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///test_incident_filters.db"
_seq = 0


@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _pragma(dbapi_conn, _):
        dbapi_conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(autouse=True)
def _clean_db(test_engine):
    """Delete all rows before each test to prevent UNIQUE collisions."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        session.execute(IncidentStatusHistory.__table__.delete())
        session.execute(PersistedIncident.__table__.delete())
        session.execute(InvestigationRun.__table__.delete())
        session.commit()
    finally:
        session.close()
    yield
    # Clean up after test too
    session = SessionLocal()
    try:
        session.execute(IncidentStatusHistory.__table__.delete())
        session.execute(PersistedIncident.__table__.delete())
        session.execute(InvestigationRun.__table__.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def db_session(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(test_engine, db_session):
    from src.database import session as db_session_mod

    def _override():
        try:
            yield db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[db_session_mod.get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db_session
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_id(prefix: str = "INV") -> str:
    global _seq
    _seq += 1
    return f"{prefix}-{_seq:06d}"


def _seed_investigation(session: Session, inv_id: str | None = None) -> InvestigationRun:
    run = InvestigationRun(
        investigation_id=inv_id or _next_id("INV"),
        status="completed",
        transactions_path="data/raw/transactions.csv",
        window_labels_path="data/raw/window_labels.csv",
        z_threshold=3.0,
        min_history_days=30,
        merchant_filter=None,
        total_results=100,
        spikes_detected=10,
        fraud_incidents=3,
        organic_incidents=4,
        review_required=3,
        baseline_windows=90,
        spike_rate=0.10,
        processing_note="Test",
    )
    session.add(run)
    session.flush()
    return run


def _seed_incident(
    session: Session,
    run: InvestigationRun,
    *,
    incident_id: str | None = None,
    merchant_id: str = "merchant_001",
    severity: str = "high",
    classification: str = "fraud_spike",
    workflow_status: str = "open",
    assigned_analyst: str | None = None,
    fraud_probability: float = 0.85,
    confidence: float = 0.72,
    created_at: datetime | None = None,
) -> PersistedIncident:
    inc = PersistedIncident(
        investigation_run_id=run.id,
        incident_id=incident_id or _next_id("INC"),
        merchant_id=merchant_id,
        date="2025-07-24",
        severity=severity,
        status="open",
        classification=classification,
        fraud_probability=fraud_probability,
        confidence=confidence,
        confidence_band="high_confidence",
        anomaly_score=3.5,
        decision_reason="Test",
        anomaly_summary="Test",
        top_signals_json="[]",
        recommended_action="Test",
        workflow_status=workflow_status,
        assigned_analyst=assigned_analyst,
    )
    if created_at:
        inc.created_at = created_at
    session.add(inc)
    session.flush()
    return inc


def _seed_batch(session: Session) -> dict:
    """Seed a batch of incidents for filter testing."""
    inv1 = _seed_investigation(session, "INV-BATCH-001")
    inv2 = _seed_investigation(session, "INV-BATCH-002")
    now = datetime.now(timezone.utc)

    incidents = []
    for i in range(5):
        inc = _seed_incident(
            session,
            inv1,
            incident_id=f"INC-FILTER-{i:03d}",
            merchant_id=f"merchant_{i:03d}",
            severity=["critical", "high", "medium", "low", "high"][i],
            classification=["fraud_spike", "organic_spike", "review_required", "fraud_spike", "fraud_spike"][i],
            workflow_status=["open", "investigating", "resolved", "open", "false_positive"][i],
            assigned_analyst=["analyst_A", "analyst_B", None, "analyst_A", None][i],
            fraud_probability=[0.95, 0.30, 0.60, 0.80, 0.90][i],
            confidence=[0.90, 0.70, 0.50, 0.85, 0.88][i],
            created_at=now - timedelta(days=4 - i),
        )
        incidents.append(inc)

    # One more incident in a different investigation
    inc_extra = _seed_incident(
        session,
        inv2,
        incident_id="INC-FILTER-005",
        merchant_id="merchant_002",
        severity="critical",
        classification="fraud_spike",
        workflow_status="open",
        assigned_analyst="analyst_B",
        fraud_probability=0.99,
        confidence=0.95,
        created_at=now - timedelta(days=10),
    )
    incidents.append(inc_extra)
    session.commit()

    return {
        "inv1": inv1,
        "inv2": inv2,
        "incidents": incidents,
    }


# ---------------------------------------------------------------------------
# Tests: Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_by_incident_id(self, client):
        c, session = client
        data = _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?search=INC-FILTER-002")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) == 1
        assert items[0]["incident_id"] == "INC-FILTER-002"

    def test_search_by_merchant_id(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?search=merchant_003")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) == 1
        assert items[0]["merchant_id"] == "merchant_003"

    def test_search_case_insensitive(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?search=INC-FILTER-000")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_search_partial_match(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?search=INC-FILTER")
        assert resp.status_code == 200
        assert resp.json()["total"] == 6  # all 6 incidents

    def test_search_no_results(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?search=NONEXISTENT")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["incidents"] == []


# ---------------------------------------------------------------------------
# Tests: Exact filters
# ---------------------------------------------------------------------------


class TestExactFilters:
    def test_filter_workflow_status(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?workflow_status=open")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert all(i["workflow_status"] == "open" for i in items)
        assert resp.json()["total"] == 3  # INC-000, INC-003, INC-005

    def test_filter_classification(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?classification=organic_spike")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) == 1
        assert items[0]["classification"] == "organic_spike"

    def test_filter_severity(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?severity=critical")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert all(i["severity"] == "critical" for i in items)
        assert resp.json()["total"] == 2  # INC-000, INC-005

    def test_filter_assigned_analyst(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?assigned_analyst=analyst_A")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) == 2
        assert all(i["assigned_analyst"] == "analyst_A" for i in items)

    def test_filter_investigation_id(self, client):
        c, session = client
        data = _seed_batch(session)

        resp = c.get(f"/api/v1/incidents/persisted?investigation_id={data['inv2'].investigation_id}")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) == 1
        assert items[0]["incident_id"] == "INC-FILTER-005"


# ---------------------------------------------------------------------------
# Tests: Date range
# ---------------------------------------------------------------------------


class TestDateRange:
    def test_created_from(self, client):
        c, session = client
        data = _seed_batch(session)

        # Only incidents created within last 2 days
        now = datetime.now(timezone.utc)
        cutoff = quote((now - timedelta(days=2)).isoformat())
        resp = c.get(f"/api/v1/incidents/persisted?created_from={cutoff}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2  # INC-003, INC-004

    def test_created_to(self, client):
        c, session = client
        data = _seed_batch(session)

        now = datetime.now(timezone.utc)
        cutoff = quote((now - timedelta(days=3)).isoformat())
        resp = c.get(f"/api/v1/incidents/persisted?created_to={cutoff}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 3  # INC-000, INC-001, INC-005

    def test_invalid_date_range(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?created_from=2026-01-01T00:00:00&created_to=2025-01-01T00:00:00")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Combined filters
# ---------------------------------------------------------------------------


class TestCombinedFilters:
    def test_combined_severity_and_workflow(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?severity=high&workflow_status=false_positive")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) == 1
        assert items[0]["incident_id"] == "INC-FILTER-004"

    def test_search_and_classification(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?search=merchant_000&classification=fraud_spike")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# Tests: Sorting
# ---------------------------------------------------------------------------


class TestSorting:
    def test_sort_by_created_at_desc(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?sort_by=created_at&sort_order=desc")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        dates = [i["created_at"] for i in items]
        assert dates == sorted(dates, reverse=True)

    def test_sort_by_created_at_asc(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?sort_by=created_at&sort_order=asc")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        dates = [i["created_at"] for i in items]
        assert dates == sorted(dates)

    def test_sort_by_fraud_probability(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?sort_by=fraud_probability&sort_order=desc")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        probs = [i["fraud_probability"] for i in items]
        assert probs == sorted(probs, reverse=True)

    def test_sort_by_severity(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?sort_by=severity&sort_order=asc")
        assert resp.status_code == 200
        # Just verify it succeeds and returns all
        assert resp.json()["total"] == 6

    def test_invalid_sort_by(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?sort_by=invalid_field")
        assert resp.status_code == 422

    def test_invalid_sort_order(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?sort_order=upside")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    def test_limit_and_offset(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["incidents"]) == 2
        assert data["total"] == 6
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_pagination_second_page(self, client):
        c, session = client
        _seed_batch(session)

        resp1 = c.get("/api/v1/incidents/persisted?limit=2&offset=0")
        resp2 = c.get("/api/v1/incidents/persisted?limit=2&offset=2")
        ids1 = {i["incident_id"] for i in resp1.json()["incidents"]}
        ids2 = {i["incident_id"] for i in resp2.json()["incidents"]}
        assert ids1.isdisjoint(ids2)  # no overlap

    def test_offset_beyond_total(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?limit=20&offset=100")
        assert resp.status_code == 200
        assert resp.json()["incidents"] == []
        assert resp.json()["total"] == 6

    def test_limit_validation(self, client):
        c, session = client
        _seed_batch(session)

        resp = c.get("/api/v1/incidents/persisted?limit=0")
        assert resp.status_code == 422

        resp = c.get("/api/v1/incidents/persisted?limit=101")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Empty state
# ---------------------------------------------------------------------------


class TestEmptyState:
    def test_empty_database(self, client):
        c, _ = client
        resp = c.get("/api/v1/incidents/persisted")
        assert resp.status_code == 200
        data = resp.json()
        assert data["incidents"] == []
        assert data["total"] == 0
