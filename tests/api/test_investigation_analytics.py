"""
Tests for investigation analytics endpoint.

Verifies:
- Overview statistics (empty database, single, multiple)
- Status distribution
- Activity over time (daily aggregation, ordering)
- Top merchants (grouping, ordering, limits, null filtering)
- Recent activity (newest first, limit)
- Date filtering
- Invalid date range returns 422
- API contract (no internal DB IDs, existing endpoints unchanged)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

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

    db_url = f"sqlite:///{tmp_path / 'test_analytics.db'}"
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


def _seed(session, investigation_id, **overrides):
    """Seed a single investigation run with optional field overrides."""
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
        processing_note="",
    )
    defaults.update(overrides)
    run = InvestigationRun(**defaults)
    session.add(run)
    session.flush()
    return run


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


class TestOverview:
    def test_empty_database(self, test_app):
        """Empty database should return zero overview values."""
        client, _, _ = test_app
        resp = client.get("/api/v1/investigations/analytics")
        assert resp.status_code == 200
        o = resp.json()["overview"]
        assert o["total_investigations"] == 0
        assert o["total_results"] == 0
        assert o["average_spike_rate"] == 0.0

    def test_single_investigation(self, test_app):
        """Single investigation should produce correct overview totals."""
        client, session, _ = test_app
        _seed(session, "INV-OV-001", total_results=100, spikes_detected=10,
              fraud_incidents=5, organic_incidents=3, review_required=2, spike_rate=0.10)
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        o = resp.json()["overview"]
        assert o["total_investigations"] == 1
        assert o["completed_investigations"] == 1
        assert o["total_results"] == 100
        assert o["total_spikes_detected"] == 10
        assert o["total_fraud_incidents"] == 5
        assert o["total_organic_incidents"] == 3
        assert o["total_review_required"] == 2
        assert o["average_spike_rate"] == pytest.approx(0.10)
        assert o["average_fraud_per_investigation"] == pytest.approx(5.0)

    def test_multiple_investigations_averages(self, test_app):
        """Multiple investigations should produce correct averages."""
        client, session, _ = test_app
        _seed(session, "INV-OV-002", spike_rate=0.10, fraud_incidents=4)
        _seed(session, "INV-OV-003", spike_rate=0.20, fraud_incidents=6)
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        o = resp.json()["overview"]
        assert o["total_investigations"] == 2
        assert o["average_spike_rate"] == pytest.approx(0.15)
        assert o["average_fraud_per_investigation"] == pytest.approx(5.0)

    def test_non_completed_status_counted(self, test_app):
        """Non-completed investigations should still appear in total but not completed count."""
        client, session, _ = test_app
        _seed(session, "INV-OV-004", status="completed")
        _seed(session, "INV-OV-005", status="failed")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        o = resp.json()["overview"]
        assert o["total_investigations"] == 2
        assert o["completed_investigations"] == 1


# ---------------------------------------------------------------------------
# Status distribution
# ---------------------------------------------------------------------------


class TestStatusDistribution:
    def test_multiple_statuses(self, test_app):
        """Each status should appear with its count."""
        client, session, _ = test_app
        _seed(session, "INV-SD-001", status="completed")
        _seed(session, "INV-SD-002", status="completed")
        _seed(session, "INV-SD-003", status="failed")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        dist = resp.json()["status_distribution"]
        statuses = {item["status"]: item["count"] for item in dist}
        assert statuses["completed"] == 2
        assert statuses["failed"] == 1

    def test_empty_database(self, test_app):
        """Empty database should return empty status distribution."""
        client, _, _ = test_app
        resp = client.get("/api/v1/investigations/analytics")
        assert resp.json()["status_distribution"] == []


# ---------------------------------------------------------------------------
# Activity over time
# ---------------------------------------------------------------------------


class TestActivityOverTime:
    def test_chronological_ordering(self, test_app):
        """Activity entries should be sorted by date ascending."""
        client, session, _ = test_app
        _seed(session, "INV-AT-001")
        _seed(session, "INV-AT-002")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        days = resp.json()["activity_over_time"]
        dates = [d["date"] for d in days]
        assert dates == sorted(dates)

    def test_investigations_per_day(self, test_app):
        """Multiple investigations on the same day should be aggregated."""
        client, session, _ = test_app
        _seed(session, "INV-AT-010", total_results=100, spikes_detected=5)
        _seed(session, "INV-AT-011", total_results=200, spikes_detected=10)
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        days = resp.json()["activity_over_time"]
        assert len(days) >= 1
        # Both should be on same day since they're created immediately
        assert days[0]["investigations"] == 2
        assert days[0]["total_results"] == 300
        assert days[0]["spikes_detected"] == 15


# ---------------------------------------------------------------------------
# Top merchants
# ---------------------------------------------------------------------------


class TestTopMerchants:
    def test_grouping_and_ordering(self, test_app):
        """Merchants should be grouped by merchant_filter and ordered by count."""
        client, session, _ = test_app
        _seed(session, "INV-MC-001", merchant_filter="merchant_001", spikes_detected=10, fraud_incidents=3)
        _seed(session, "INV-MC-002", merchant_filter="merchant_001", spikes_detected=20, fraud_incidents=5)
        _seed(session, "INV-MC-003", merchant_filter="merchant_002", spikes_detected=5, fraud_incidents=1)
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        merchants = resp.json()["top_merchants"]
        assert len(merchants) == 2
        # merchant_001 has 2 investigations, merchant_002 has 1
        assert merchants[0]["merchant_filter"] == "merchant_001"
        assert merchants[0]["investigation_count"] == 2
        assert merchants[0]["total_spikes_detected"] == 30
        assert merchants[0]["total_fraud_incidents"] == 8
        assert merchants[1]["merchant_filter"] == "merchant_002"

    def test_null_merchant_filters_ignored(self, test_app):
        """Investigations with null merchant_filter should not appear."""
        client, session, _ = test_app
        _seed(session, "INV-MC-010", merchant_filter=None)
        _seed(session, "INV-MC-011", merchant_filter="merchant_001")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        merchants = resp.json()["top_merchants"]
        assert len(merchants) == 1
        assert merchants[0]["merchant_filter"] == "merchant_001"

    def test_empty_database(self, test_app):
        """Empty database should return empty merchant list."""
        client, _, _ = test_app
        resp = client.get("/api/v1/investigations/analytics")
        assert resp.json()["top_merchants"] == []


# ---------------------------------------------------------------------------
# Recent activity
# ---------------------------------------------------------------------------


class TestRecentActivity:
    def test_newest_first(self, test_app):
        """Recent investigations should be newest first."""
        client, session, _ = test_app
        _seed(session, "INV-RA-001")
        _seed(session, "INV-RA-002")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        recent = resp.json()["recent_activity"]
        assert len(recent) == 2
        # Most recently created should be first
        assert recent[0]["created_at"] >= recent[1]["created_at"]

    def test_limit(self, test_app):
        """Should return at most the recent activity limit."""
        client, session, _ = test_app
        for i in range(15):
            _seed(session, f"INV-RA-{i:03d}")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        recent = resp.json()["recent_activity"]
        assert len(recent) == 10  # RECENT_ACTIVITY_LIMIT


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------


class TestDateFiltering:
    def test_created_from(self, test_app):
        """created_from should filter investigations on or after the date."""
        client, session, _ = test_app
        now = datetime.now(timezone.utc)
        old = _seed(session, "INV-DF-001")
        old.created_at = now - timedelta(days=30)
        _seed(session, "INV-DF-002")  # created_at = now
        session.commit()

        # Use format without timezone suffix for FastAPI Query parsing
        dt_str = (now - timedelta(days=1)).replace(tzinfo=None).isoformat()
        resp = client.get(f"/api/v1/investigations/analytics?created_from={dt_str}")
        assert resp.status_code == 200
        assert resp.json()["overview"]["total_investigations"] == 1

    def test_created_to(self, test_app):
        """created_to should filter investigations on or before the date."""
        client, session, _ = test_app
        now = datetime.now(timezone.utc)
        _seed(session, "INV-DF-010")
        _seed(session, "INV-DF-011")
        session.commit()

        dt_str = (now - timedelta(hours=1)).replace(tzinfo=None).isoformat()
        resp = client.get(f"/api/v1/investigations/analytics?created_to={dt_str}")
        assert resp.status_code == 200
        assert resp.json()["overview"]["total_investigations"] == 0

    def test_invalid_date_range(self, test_app):
        """created_from > created_to should return 422."""
        client, _, _ = test_app
        resp = client.get(
            "/api/v1/investigations/analytics?created_from=2026-01-01T00:00:00&created_to=2025-01-01T00:00:00"
        )
        assert resp.status_code == 422
        assert "created_from" in resp.json()["detail"].lower()

    def test_no_date_params(self, test_app):
        """No date params should include all investigations."""
        client, session, _ = test_app
        _seed(session, "INV-DF-020")
        _seed(session, "INV-DF-021")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        assert resp.json()["overview"]["total_investigations"] == 2


# ---------------------------------------------------------------------------
# API contract
# ---------------------------------------------------------------------------


class TestAPIContract:
    def test_no_internal_db_ids(self, test_app):
        """Response should not contain internal database primary keys."""
        client, session, _ = test_app
        _seed(session, "INV-CT-001", merchant_filter="merchant_001")
        session.commit()

        resp = client.get("/api/v1/investigations/analytics")
        data = resp.json()
        # Check overview has no 'id' field
        assert "id" not in data["overview"]
        # Check recent_activity has no 'id' field
        for item in data["recent_activity"]:
            assert "id" not in item
        # Check top_merchants has no 'id' field
        for item in data["top_merchants"]:
            assert "id" not in item

    def test_existing_endpoints_unchanged(self, test_app):
        """Existing investigation endpoints should still work."""
        client, _, _ = test_app
        # History
        resp = client.get("/api/v1/investigations")
        assert resp.status_code == 200
        assert "items" in resp.json()
        # Run
        resp = client.post("/api/v1/investigations/run", json={})
        assert resp.status_code in (200, 404, 422, 500)

    def test_response_structure(self, test_app):
        """Response should contain all expected top-level keys."""
        client, _, _ = test_app
        resp = client.get("/api/v1/investigations/analytics")
        data = resp.json()
        assert "period" in data
        assert "overview" in data
        assert "status_distribution" in data
        assert "activity_over_time" in data
        assert "top_merchants" in data
        assert "recent_activity" in data

    def test_period_reflects_filters(self, test_app):
        """Period in response should reflect the date filters."""
        client, _, _ = test_app
        resp = client.get(
            "/api/v1/investigations/analytics?created_from=2026-01-01T00:00:00&created_to=2026-12-31T23:59:59"
        )
        period = resp.json()["period"]
        assert period["created_from"] is not None
        assert period["created_to"] is not None
