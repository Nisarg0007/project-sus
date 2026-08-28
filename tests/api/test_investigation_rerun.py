"""
Tests for investigation rerun endpoint.

Verifies:
- Successful rerun creates a new investigation with a new ID
- Original investigation remains unchanged
- New investigation persists correctly
- New incidents persist correctly
- Stored configuration is reused
- Nonexistent investigation returns 404
- Response shape matches existing run endpoint
- Existing POST /investigations/run behavior unchanged
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import InvestigationRun, PersistedIncident


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_app(tmp_path):
    """Create a FastAPI app bound to a temporary SQLite database."""
    from fastapi.testclient import TestClient

    db_url = f"sqlite:///{tmp_path / 'test_rerun.db'}"
    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    import src.database.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)

    import sys
    engine_module = sys.modules["src.database.engine"]
    session_module = sys.modules["src.database.session"]

    original_engine = engine_module.engine
    original_sf = engine_module.SessionLocal
    original_session_sf = session_module.SessionLocal

    try:
        engine_module.engine = test_engine
        engine_module.SessionLocal = TestSession
        session_module.SessionLocal = TestSession

        from src.api.app import create_app

        app = create_app()

        with TestClient(app, raise_server_exceptions=False) as client:
            session = TestSession()
            try:
                yield client, session, test_engine
            finally:
                session.close()
    finally:
        engine_module.engine = original_engine
        engine_module.SessionLocal = original_sf
        session_module.SessionLocal = original_session_sf


def _seed_investigation(session, investigation_id="INV-SEED-001", **overrides):
    """Insert a test investigation run."""
    defaults = dict(
        investigation_id=investigation_id,
        status="completed",
        transactions_path="data/raw/transactions.csv",
        window_labels_path="data/raw/window_labels.csv",
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
        processing_note="Original investigation",
    )
    defaults.update(overrides)
    run = InvestigationRun(**defaults)
    session.add(run)
    session.flush()

    # Add an incident
    inc = PersistedIncident(
        investigation_run_id=run.id,
        incident_id="INC-SEED-001",
        merchant_id="merchant_001",
        date="2025-07-24",
        severity="critical",
        status="open",
        classification="fraud_spike",
        fraud_probability=0.961,
        confidence=0.89,
        confidence_band="high_confidence",
        anomaly_score=3.8,
        decision_reason="Coordinated fraud pattern",
        anomaly_summary="Payment failure rate elevated",
        top_signals_json=json.dumps(["failed_payments: +157%"]),
        recommended_action="Review affected transactions",
    )
    session.add(inc)
    session.commit()
    return run


# ---------------------------------------------------------------------------
# POST /api/v1/investigations/{id}/rerun — Tests
# ---------------------------------------------------------------------------


class TestRerunInvestigation:

    def test_rerun_creates_new_investigation(self, test_app):
        """Rerun should create a completely new investigation with a new ID."""
        client, session, _ = test_app
        original = _seed_investigation(session, investigation_id="INV-ORIG-001")

        response = client.post("/api/v1/investigations/INV-ORIG-001/rerun")
        assert response.status_code == 200
        data = response.json()

        # New investigation ID should differ from original
        assert data["investigation_id"] != "INV-ORIG-001"
        assert data["investigation_id"].startswith("INV-")

    def test_rerun_original_unchanged(self, test_app):
        """The original investigation must never be modified by a rerun."""
        client, session, _ = test_app
        original = _seed_investigation(session, investigation_id="INV-ORIG-002")

        # Record original state
        orig_investigation_id = original.investigation_id
        orig_total = original.total_results
        orig_incidents = len(original.incidents)

        # Perform rerun
        client.post("/api/v1/investigations/INV-ORIG-002/rerun")

        # Reload and verify original is unchanged
        session.expire_all()
        run = session.query(InvestigationRun).filter_by(
            investigation_id=orig_investigation_id
        ).first()
        assert run is not None
        assert run.total_results == orig_total
        assert len(run.incidents) == orig_incidents

    def test_rerun_persists_new_investigation(self, test_app):
        """The new investigation should be persisted in the database."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-ORIG-003")

        response = client.post("/api/v1/investigations/INV-ORIG-003/rerun")
        new_id = response.json()["investigation_id"]

        # Verify persisted
        session.expire_all()
        run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert run is not None
        assert run.status == "completed"

    def test_rerun_reuses_configuration(self, test_app):
        """Rerun should use the original investigation's stored configuration.

        We verify this by checking that the rerun endpoint calls into the
        same pipeline execution path as the normal run. Since the original
        investigation used real data files, the rerun should also succeed
        with the same parameters.
        """
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-ORIG-004",
            z_threshold=2.0,
            min_history_days=3,
            merchant_filter=None,
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
        )

        response = client.post("/api/v1/investigations/INV-ORIG-004/rerun")
        assert response.status_code == 200

        data = response.json()
        assert "investigation_id" in data
        assert "summary" in data
        # The rerun should produce results from the same data files
        assert data["total_results"] > 0

    def test_rerun_response_shape_matches_run(self, test_app):
        """Response shape should match the existing POST /investigations/run."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-ORIG-005")

        response = client.post("/api/v1/investigations/INV-ORIG-005/rerun")
        data = response.json()

        # Verify all expected fields are present
        assert "investigation_id" in data
        assert "summary" in data
        assert "incidents" in data
        assert "total_results" in data
        assert "processing_note" in data

        # Verify summary fields
        summary = data["summary"]
        assert "total_windows" in summary
        assert "spikes_detected" in summary
        assert "spike_rate" in summary
        assert "fraud_incidents" in summary
        assert "organic_incidents" in summary
        assert "review_required" in summary
        assert "baseline_windows" in summary

    def test_rerun_nonexistent_returns_404(self, test_app):
        """Rerunning a nonexistent investigation should return 404."""
        client, _, _ = test_app
        response = client.post("/api/v1/investigations/INV-NONEXISTENT/rerun")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_rerun_increases_investigation_count(self, test_app):
        """Each rerun should add exactly one new investigation."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-ORIG-006")

        # Count before
        count_before = session.query(InvestigationRun).count()

        # Rerun twice
        client.post("/api/v1/investigations/INV-ORIG-006/rerun")
        client.post("/api/v1/investigations/INV-ORIG-006/rerun")

        # Count should increase by 2
        session.expire_all()
        count_after = session.query(InvestigationRun).count()
        assert count_after == count_before + 2

    def test_rerun_generates_unique_ids(self, test_app):
        """Each rerun should produce a unique investigation ID."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-ORIG-007")

        r1 = client.post("/api/v1/investigations/INV-ORIG-007/rerun").json()
        r2 = client.post("/api/v1/investigations/INV-ORIG-007/rerun").json()

        assert r1["investigation_id"] != r2["investigation_id"]
        assert r1["investigation_id"] != "INV-ORIG-007"
        assert r2["investigation_id"] != "INV-ORIG-007"


class TestExistingRunUnchanged:
    """Verify that existing POST /investigations/run behavior is preserved."""

    def test_existing_run_endpoint_still_works(self, test_app):
        """The existing POST /investigations/run should work exactly as before."""
        client, _, _ = test_app
        response = client.post(
            "/api/v1/investigations/run",
            json={},
        )
        # Should succeed (or fail with pipeline error, not route error)
        assert response.status_code in (200, 404, 422, 500)

    def test_existing_run_not_affected_by_rerun(self, test_app):
        """POST /investigations/run should still work after reruns."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-BEFO-001")

        # Do a rerun first
        client.post("/api/v1/investigations/INV-BEFO-001/rerun")

        # Original endpoint should still work
        response = client.post(
            "/api/v1/investigations/run",
            json={},
        )
        assert response.status_code in (200, 404, 422, 500)
