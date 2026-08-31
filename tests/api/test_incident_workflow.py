"""
Tests for incident workflow management.

Covers:
- GET /incidents/{incident_id} — detail retrieval
- PATCH /incidents/{incident_id} — workflow updates
- GET /incidents/{incident_id}/history — status transition audit trail
- Validation: invalid transitions, resolution consistency, 404
- GET /incidents/persisted — persisted incident list
- Existing GET /incidents compatibility
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.api.app import create_app
from src.database.base import Base
from src.database.models import (
    InvestigationRun,
    PersistedIncident,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///test_incident_workflow.db"
_seq = 0  # global counter for unique IDs


@pytest.fixture(scope="module")
def test_engine():
    eng = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


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

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[db_session_mod.get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, db_session, test_engine
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers — each call gets a unique investigation_id
# ---------------------------------------------------------------------------

def _next_id(prefix: str = "INV") -> str:
    global _seq
    _seq += 1
    return f"{prefix}-{_seq:06d}"


def _seed_investigation(session: Session, investigation_id: str | None = None) -> InvestigationRun:
    inv_id = investigation_id or _next_id("INV")
    run = InvestigationRun(
        investigation_id=inv_id,
        status="completed",
        transactions_path="data/raw/transactions.csv",
        window_labels_path="data/raw/window_labels.csv",
        z_threshold=3.0,
        min_history_days=30,
        merchant_filter="merchant_001",
        total_results=100,
        spikes_detected=10,
        fraud_incidents=3,
        organic_incidents=4,
        review_required=3,
        baseline_windows=90,
        spike_rate=0.10,
        processing_note="Test run",
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
    workflow_status: str = "open",
) -> PersistedIncident:
    inc_id = incident_id or _next_id("INC")
    inc = PersistedIncident(
        investigation_run_id=run.id,
        incident_id=inc_id,
        merchant_id=merchant_id,
        date="2025-07-24",
        severity="high",
        status="open",
        classification="fraud_spike",
        predicted_cause="suspicious_transaction_pattern",
        fraud_probability=0.85,
        confidence=0.72,
        confidence_band="high_confidence",
        anomaly_score=3.5,
        decision_reason="High fraud probability with elevated anomaly score",
        anomaly_summary="Transaction volume 4.2x baseline; failed payment rate elevated 180%",
        top_signals_json='["Volume spike 4.2x baseline", "Failed payment rate +180%"]',
        recommended_action="Immediate manual review recommended",
        workflow_status=workflow_status,
    )
    session.add(inc)
    session.flush()
    return inc


# ---------------------------------------------------------------------------
# Tests: GET /incidents/{incident_id} — detail
# ---------------------------------------------------------------------------


class TestIncidentDetail:
    def test_get_incident_detail(self, client):
        c, session, _ = client
        inv_id = _next_id()
        run = _seed_investigation(session, inv_id)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_id"] == inc.incident_id
        assert data["merchant_id"] == "merchant_001"
        assert data["severity"] == "high"
        assert data["classification"] == "fraud_spike"
        assert data["workflow_status"] == "open"
        assert data["fraud_probability"] == 0.85
        assert data["confidence"] == 0.72
        assert data["assigned_analyst"] is None
        assert data["analyst_notes"] is None
        assert data["resolution"] is None
        assert data["status_history"] == []

    def test_get_incident_not_found(self, client):
        c, _, _ = client
        resp = c.get("/api/v1/incidents/INC-NONEXISTENT-999")
        assert resp.status_code == 404

    def test_detail_includes_workflow_fields(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run, workflow_status="investigating")
        inc.assigned_analyst = "analyst_001"
        inc.analyst_notes = "Reviewing linked transactions"
        session.commit()

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_status"] == "investigating"
        assert data["assigned_analyst"] == "analyst_001"
        assert data["analyst_notes"] == "Reviewing linked transactions"
        assert "updated_at" in data

    def test_detail_does_not_expose_pk(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        data = resp.json()
        # Must not expose internal IDs
        assert "investigation_run_id" not in data

    def test_detail_top_signals_deserialized(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        data = resp.json()
        assert isinstance(data["top_signals"], list)
        assert len(data["top_signals"]) == 2


# ---------------------------------------------------------------------------
# Tests: PATCH /incidents/{incident_id} — update
# ---------------------------------------------------------------------------


class TestIncidentUpdate:
    def test_update_status_to_investigating(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "investigating"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_status"] == "investigating"
        assert data["assigned_analyst"] is None

    def test_update_assignment(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"assigned_analyst": "analyst_001"},
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_analyst"] == "analyst_001"
        assert resp.json()["workflow_status"] == "open"

    def test_update_notes(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": "Reviewing linked transactions."},
        )
        assert resp.status_code == 200
        assert resp.json()["analyst_notes"] == "Reviewing linked transactions."

    def test_partial_update_preserves_other_fields(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        inc.assigned_analyst = "analyst_002"
        inc.analyst_notes = "Original notes"
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": "Updated notes"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["analyst_notes"] == "Updated notes"
        assert data["assigned_analyst"] == "analyst_002"

    def test_update_not_found(self, client):
        c, _, _ = client
        resp = c.patch(
            "/api/v1/incidents/INC-NONEXISTENT-999",
            json={"workflow_status": "investigating"},
        )
        assert resp.status_code == 404

    def test_clear_assignment(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        inc.assigned_analyst = "analyst_001"
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"assigned_analyst": None},
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_analyst"] is None


# ---------------------------------------------------------------------------
# Tests: Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_open_to_investigating(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "investigating"},
        )
        assert resp.status_code == 200
        assert resp.json()["workflow_status"] == "investigating"

    def test_open_to_resolved(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "resolved", "resolution": "confirmed_fraud"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_status"] == "resolved"
        assert data["resolution"] == "confirmed_fraud"

    def test_open_to_false_positive(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "false_positive", "resolution": "false_positive"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_status"] == "false_positive"

    def test_invalid_transition_rejected(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run, workflow_status="resolved")
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "false_positive"},
        )
        assert resp.status_code == 422

    def test_resolution_on_open_rejected(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"resolution": "confirmed_fraud"},
        )
        assert resp.status_code == 422

    def test_resolution_on_resolved_accepted(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run, workflow_status="resolved")
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"resolution": "inconclusive"},
        )
        assert resp.status_code == 200
        assert resp.json()["resolution"] == "inconclusive"


# ---------------------------------------------------------------------------
# Tests: Status history / audit trail
# ---------------------------------------------------------------------------


class TestStatusHistory:
    def test_status_change_creates_history(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "investigating"},
        )
        assert resp.status_code == 200

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        history = resp.json()["status_history"]
        assert len(history) == 1
        assert history[0]["old_status"] == "open"
        assert history[0]["new_status"] == "investigating"

    def test_multiple_transitions(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        # open → investigating
        c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "investigating", "assigned_analyst": "a1"},
        )
        # investigating → resolved
        c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "resolved", "resolution": "confirmed_fraud"},
        )

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        history = resp.json()["status_history"]
        assert len(history) == 2
        assert history[0]["old_status"] == "open"
        assert history[0]["new_status"] == "investigating"
        assert history[1]["old_status"] == "investigating"
        assert history[1]["new_status"] == "resolved"

    def test_no_history_when_status_unchanged(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": "Some notes"},
        )

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}")
        assert len(resp.json()["status_history"]) == 0

    def test_history_endpoint(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "investigating"},
        )

        resp = c.get(f"/api/v1/incidents/{inc.incident_id}/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 1
        assert history[0]["old_status"] == "open"
        assert history[0]["new_status"] == "investigating"

    def test_history_endpoint_not_found(self, client):
        c, _, _ = client
        resp = c.get("/api/v1/incidents/INC-NONE-999/history")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Persisted incident list
# ---------------------------------------------------------------------------


class TestPersistedList:
    def test_list_persisted_incidents(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc1 = _seed_incident(session, run)
        inc2 = _seed_incident(session, run, merchant_id="merchant_002")
        session.commit()

        resp = c.get("/api/v1/incidents/persisted")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        ids = {i["incident_id"] for i in data["incidents"]}
        assert inc1.incident_id in ids
        assert inc2.incident_id in ids

    def test_list_persisted_with_workflow_filter(self, client):
        c, session, _ = client
        run = _seed_investigation(session)
        inc_open = _seed_incident(session, run, workflow_status="open")
        inc_inv = _seed_incident(session, run, merchant_id="merchant_003", workflow_status="investigating")
        session.commit()

        resp = c.get("/api/v1/incidents/persisted?workflow_status=investigating")
        assert resp.status_code == 200
        data = resp.json()
        inv_ids = {i["incident_id"] for i in data["incidents"]}
        assert inc_inv.incident_id in inv_ids
        assert inc_open.incident_id not in inv_ids


# ---------------------------------------------------------------------------
# Tests: Existing GET /incidents compatibility
# ---------------------------------------------------------------------------


class TestExistingIncidentsCompat:
    def test_existing_incidents_endpoint_still_works(self, client):
        c, _, _ = client
        resp = c.get("/api/v1/incidents")
        assert resp.status_code == 200
        data = resp.json()
        assert "incidents" in data
        assert "total" in data


# ---------------------------------------------------------------------------
# Tests: Analyst notes clearing
# ---------------------------------------------------------------------------


class TestAnalystNotesClearing:
    def test_notes_omitted_preserves_existing(self, client):
        """Omitting analyst_notes in the PATCH must not change existing notes."""
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        inc.analyst_notes = "Original notes"
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"workflow_status": "investigating"},
        )
        assert resp.status_code == 200
        assert resp.json()["analyst_notes"] == "Original notes"

    def test_notes_null_clears_existing(self, client):
        """Sending null for analyst_notes must clear existing notes to null."""
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        inc.analyst_notes = "Notes to clear"
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": None},
        )
        assert resp.status_code == 200
        assert resp.json()["analyst_notes"] is None

    def test_notes_empty_string_clears_existing(self, client):
        """Sending empty string for analyst_notes must clear existing notes."""
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        inc.analyst_notes = "Notes to clear"
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["analyst_notes"] is None

    def test_notes_whitespace_clears_existing(self, client):
        """Sending only whitespace for analyst_notes must clear existing notes."""
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        inc.analyst_notes = "Notes to clear"
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": "   "},
        )
        assert resp.status_code == 200
        assert resp.json()["analyst_notes"] is None

    def test_notes_nonempty_sets_value(self, client):
        """Sending a non-empty string for analyst_notes must set that value."""
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.patch(
            f"/api/v1/incidents/{inc.incident_id}",
            json={"analyst_notes": "New investigation notes"},
        )
        assert resp.status_code == 200
        assert resp.json()["analyst_notes"] == "New investigation notes"


# ---------------------------------------------------------------------------
# Tests: Persisted incident list contract
# ---------------------------------------------------------------------------


class TestPersistedListContract:
    def test_persisted_list_returns_snake_case_fields(self, client):
        """Persisted list response must use snake_case field names."""
        c, session, _ = client
        run = _seed_investigation(session)
        inc = _seed_incident(session, run)
        session.commit()

        resp = c.get("/api/v1/incidents/persisted")
        assert resp.status_code == 200
        items = resp.json()["incidents"]
        assert len(items) >= 1
        item = items[0]
        # Must use snake_case
        assert "fraud_probability" in item
        assert "confidence_band" in item
        assert item["fraud_probability"] == 0.85
        assert item["confidence_band"] == "high_confidence"
        # Must NOT use camelCase aliases
        assert "fraudProbability" not in item
        assert "confidenceBand" not in item
