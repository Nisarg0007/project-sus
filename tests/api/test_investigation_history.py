"""
API-level tests for investigation history endpoints.

Verifies:
- GET /api/v1/investigations returns correct paginated list
- GET /api/v1/investigations/{id} returns correct detail
- 404 for nonexistent investigations
- Response does not expose internal DB IDs
- top_signals is an array, not a JSON string
- Pagination parameters work correctly
- Empty database behavior
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

    db_url = f"sqlite:///{tmp_path / 'test_history.db'}"
    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSession = sessionmaker(bind=test_engine)

    # Import and create tables
    import src.database.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)

    # Patch the engine and session factory
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


def _seed_investigations(session, count: int = 3) -> list[str]:
    """Insert test investigation runs and return their IDs."""
    ids = []
    for i in range(count):
        run = InvestigationRun(
            investigation_id=f"INV-HIST-{i:03d}",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=2.0,
            min_history_days=3,
            total_results=100 + i,
            spikes_detected=10 + i,
            fraud_incidents=5 + i,
            organic_incidents=3 + i,
            review_required=2 + i,
            baseline_windows=90 - i,
            spike_rate=0.1 + i * 0.01,
            processing_note=f"Test investigation {i}",
        )
        session.add(run)
        session.flush()
        ids.append(run.investigation_id)

        # Add incidents to first and last
        if i == 0 or i == count - 1:
            inc = PersistedIncident(
                investigation_run_id=run.id,
                incident_id=f"INC-{i:03d}-001",
                merchant_id=f"merchant_{i + 1:03d}",
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
                top_signals_json=json.dumps(
                    ["failed_payments: +157%", "ip_diversity: -42%"]
                ),
                recommended_action="Review affected transactions",
            )
            session.add(inc)

    session.commit()
    return ids


# ---------------------------------------------------------------------------
# GET /api/v1/investigations — List
# ---------------------------------------------------------------------------


class TestListInvestigationsAPI:
    def test_empty_database(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_returns_investigations(self, test_app):
        client, session, _ = test_app
        _seed_investigations(session, count=3)

        response = client.get("/api/v1/investigations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_newest_first_ordering(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session, count=3)

        response = client.get("/api/v1/investigations")
        data = response.json()

        # Newest first
        assert data["items"][0]["investigation_id"] == ids[2]
        assert data["items"][-1]["investigation_id"] == ids[0]

    def test_limit(self, test_app):
        client, session, _ = test_app
        _seed_investigations(session, count=5)

        response = client.get("/api/v1/investigations?limit=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2

    def test_offset(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session, count=5)

        response = client.get("/api/v1/investigations?limit=2&offset=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2
        # First item should be the third-newest (index 2 in 0-based)
        assert data["items"][0]["investigation_id"] == ids[2]

    def test_no_exposed_db_ids(self, test_app):
        client, session, _ = test_app
        _seed_investigations(session)

        response = client.get("/api/v1/investigations")
        data = response.json()

        for item in data["items"]:
            # Should have investigation_id but NOT the numeric id
            assert "investigation_id" in item
            assert "id" not in item or item.get("id") is None

    def test_item_fields(self, test_app):
        client, session, _ = test_app
        _seed_investigations(session, count=1)

        response = client.get("/api/v1/investigations")
        data = response.json()
        item = data["items"][0]

        assert item["investigation_id"] == "INV-HIST-000"
        assert item["status"] == "completed"
        assert item["total_results"] == 100
        assert item["spikes_detected"] == 10
        assert item["fraud_incidents"] == 5
        assert item["organic_incidents"] == 3
        assert item["review_required"] == 2
        assert item["baseline_windows"] == 90
        assert item["processing_note"] == "Test investigation 0"

    def test_invalid_limit_zero(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations?limit=0")
        assert response.status_code == 422

    def test_invalid_limit_negative(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations?limit=-1")
        assert response.status_code == 422

    def test_invalid_offset_negative(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations?offset=-1")
        assert response.status_code == 422

    def test_limit_exceeds_max(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations?limit=101")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/investigations/{id} — Detail
# ---------------------------------------------------------------------------


class TestGetInvestigationDetailAPI:
    def test_not_found(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations/INV-NONEXISTENT")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_returns_detail(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session)

        response = client.get(f"/api/v1/investigations/{ids[0]}")
        assert response.status_code == 200
        data = response.json()
        assert data["investigation_id"] == ids[0]
        assert data["status"] == "completed"

    def test_includes_summary(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session)

        response = client.get(f"/api/v1/investigations/{ids[0]}")
        data = response.json()
        summary = data["summary"]
        assert summary["total_results"] == 100
        assert summary["spikes_detected"] == 10
        assert summary["spike_rate"] == pytest.approx(0.1)

    def test_includes_incidents(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session)

        # First investigation has an incident
        response = client.get(f"/api/v1/investigations/{ids[0]}")
        data = response.json()
        assert len(data["incidents"]) == 1

        inc = data["incidents"][0]
        assert inc["incident_id"] == "INC-000-001"
        assert inc["merchant_id"] == "merchant_001"
        assert inc["severity"] == "critical"
        assert inc["classification"] == "fraud_spike"

    def test_incidents_not_leaked(self, test_app):
        """Investigation with no incidents should return empty list."""
        client, session, _ = test_app
        ids = _seed_investigations(session)

        # Middle investigation has no incidents
        response = client.get(f"/api/v1/investigations/{ids[1]}")
        data = response.json()
        assert data["incidents"] == []

    def test_top_signals_is_array(self, test_app):
        """top_signals must be a JSON array, not a string."""
        client, session, _ = test_app
        ids = _seed_investigations(session)

        response = client.get(f"/api/v1/investigations/{ids[0]}")
        data = response.json()
        inc = data["incidents"][0]
        assert isinstance(inc["top_signals"], list)
        assert inc["top_signals"] == ["failed_payments: +157%", "ip_diversity: -42%"]

    def test_no_exposed_db_ids(self, test_app):
        """Internal database IDs should not be in the response."""
        client, session, _ = test_app
        ids = _seed_investigations(session)

        response = client.get(f"/api/v1/investigations/{ids[0]}")
        data = response.json()

        # Investigation level
        assert "id" not in data or data.get("id") is None

        # Incident level
        for inc in data["incidents"]:
            assert "id" not in inc or inc.get("id") is None
            assert "investigation_run_id" not in inc

    def test_includes_input_parameters(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session)

        response = client.get(f"/api/v1/investigations/{ids[0]}")
        data = response.json()
        assert data["transactions_path"] == "data/raw/transactions.csv"
        assert data["window_labels_path"] == "data/raw/window_labels.csv"
        assert data["z_threshold"] == 2.0
        assert data["min_history_days"] == 3
        assert data["model_path"] is None
        assert data["merchant_filter"] is None

    def test_incident_fields_complete(self, test_app):
        client, session, _ = test_app
        ids = _seed_investigations(session)

        response = client.get(f"/api/v1/investigations/{ids[0]}")
        inc = response.json()["incidents"][0]

        expected_fields = {
            "incident_id", "merchant_id", "date", "severity", "status",
            "classification", "predicted_cause", "fraud_probability",
            "confidence", "confidence_band", "anomaly_score",
            "decision_reason", "anomaly_summary", "top_signals",
            "recommended_action", "created_at",
        }
        assert expected_fields.issubset(set(inc.keys()))
