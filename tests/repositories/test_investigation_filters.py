"""
Tests for investigation history filtering.

Verifies:
- Repository: investigation ID partial search, status filter, merchant filter,
  date range, combined filters, filtered count, pagination after filtering
- API: each filter independently, combined filters, invalid date range,
  existing unfiltered behavior unchanged, pagination preserves filters
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

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
def repo(db_session):
    return InvestigationRepository(db_session)


@pytest.fixture()
def service():
    return InvestigationHistoryService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_RUN = dict(
    investigation_id="INV-TEST001",
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


def _seed(session, **overrides):
    """Create and persist an InvestigationRun with given overrides."""
    data = {**_BASE_RUN, **overrides}
    run = InvestigationRun(**data)
    session.add(run)
    session.flush()
    return run


# ===========================================================================
# Repository — Filter tests
# ===========================================================================


class TestRepositoryFilters:
    """Tests for InvestigationRepository._apply_filters and filtered queries."""

    def test_investigation_id_partial_match(self, db_session, repo):
        _seed(db_session, investigation_id="INV-PAYMENT-2025-001")
        _seed(db_session, investigation_id="INV-PAYMENT-2025-002")
        _seed(db_session, investigation_id="INV-MERCHANT-2025-003")
        db_session.commit()

        result = repo.list_investigations(investigation_id="PAYMENT")
        assert len(result) == 2
        ids = {r.investigation_id for r in result}
        assert "INV-MERCHANT-2025-003" not in ids

    def test_investigation_id_case_insensitive(self, db_session, repo):
        _seed(db_session, investigation_id="INV-AbC-123")
        db_session.commit()

        result = repo.list_investigations(investigation_id="abc")
        assert len(result) == 1

    def test_status_exact_match(self, db_session, repo):
        _seed(db_session, investigation_id="INV-S001", status="completed")
        _seed(db_session, investigation_id="INV-S002", status="running")
        _seed(db_session, investigation_id="INV-S003", status="completed")
        db_session.commit()

        result = repo.list_investigations(status="running")
        assert len(result) == 1
        assert result[0].investigation_id == "INV-S002"

    def test_status_no_match(self, db_session, repo):
        _seed(db_session, investigation_id="INV-S004", status="completed")
        db_session.commit()

        result = repo.list_investigations(status="nonexistent")
        assert len(result) == 0

    def test_merchant_filter_partial_match(self, db_session, repo):
        _seed(db_session, investigation_id="INV-M001", merchant_filter="merchant_001")
        _seed(db_session, investigation_id="INV-M002", merchant_filter="merchant_002")
        _seed(db_session, investigation_id="INV-M003", merchant_filter=None)
        db_session.commit()

        result = repo.list_investigations(merchant_filter="merchant_001")
        assert len(result) == 1
        assert result[0].investigation_id == "INV-M001"

    def test_merchant_filter_case_insensitive(self, db_session, repo):
        _seed(db_session, investigation_id="INV-MC01", merchant_filter="Merchant_001")
        db_session.commit()

        result = repo.list_investigations(merchant_filter="merchant")
        assert len(result) == 1

    def test_created_from(self, db_session, repo):
        base = datetime(2025, 7, 15, tzinfo=timezone.utc)
        r1 = _seed(db_session, investigation_id="INV-D001")
        r1.created_at = base - timedelta(days=10)  # Jul 5
        r2 = _seed(db_session, investigation_id="INV-D002")
        r2.created_at = base  # Jul 15
        r3 = _seed(db_session, investigation_id="INV-D003")
        r3.created_at = base + timedelta(days=10)  # Jul 25
        db_session.commit()

        result = repo.list_investigations(created_from=base)
        assert len(result) == 2
        ids = {r.investigation_id for r in result}
        assert "INV-D001" not in ids
        assert "INV-D002" in ids
        assert "INV-D003" in ids

    def test_created_to(self, db_session, repo):
        base = datetime(2025, 7, 15, tzinfo=timezone.utc)
        r1 = _seed(db_session, investigation_id="INV-D004")
        r1.created_at = base - timedelta(days=10)
        r2 = _seed(db_session, investigation_id="INV-D005")
        r2.created_at = base
        r3 = _seed(db_session, investigation_id="INV-D006")
        r3.created_at = base + timedelta(days=10)
        db_session.commit()

        result = repo.list_investigations(created_to=base)
        assert len(result) == 2
        ids = {r.investigation_id for r in result}
        assert "INV-D004" in ids
        assert "INV-D005" in ids
        assert "INV-D006" not in ids

    def test_created_from_and_to_combined(self, db_session, repo):
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        r1 = _seed(db_session, investigation_id="INV-DR01")
        r1.created_at = base - timedelta(days=5)
        r2 = _seed(db_session, investigation_id="INV-DR02")
        r2.created_at = base + timedelta(days=5)
        r3 = _seed(db_session, investigation_id="INV-DR03")
        r3.created_at = base + timedelta(days=15)
        db_session.commit()

        result = repo.list_investigations(
            created_from=base, created_to=base + timedelta(days=10)
        )
        assert len(result) == 1
        assert result[0].investigation_id == "INV-DR02"

    def test_combined_filters(self, db_session, repo):
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        r1 = _seed(
            db_session,
            investigation_id="INV-CF01",
            status="completed",
            merchant_filter="merchant_001",
        )
        r1.created_at = base
        r2 = _seed(
            db_session,
            investigation_id="INV-CF02",
            status="completed",
            merchant_filter="merchant_002",
        )
        r2.created_at = base + timedelta(days=1)
        r3 = _seed(
            db_session,
            investigation_id="INV-CF03",
            status="running",
            merchant_filter="merchant_001",
        )
        r3.created_at = base
        db_session.commit()

        result = repo.list_investigations(
            status="completed",
            merchant_filter="merchant_001",
        )
        assert len(result) == 1
        assert result[0].investigation_id == "INV-CF01"

    def test_filtered_count(self, db_session, repo):
        _seed(db_session, investigation_id="INV-CT01", status="completed")
        _seed(db_session, investigation_id="INV-CT02", status="running")
        _seed(db_session, investigation_id="INV-CT03", status="completed")
        db_session.commit()

        assert repo.count_investigations(status="completed") == 2
        assert repo.count_investigations(status="running") == 1
        assert repo.count_investigations() == 3

    def test_pagination_after_filtering(self, db_session, repo):
        for i in range(5):
            _seed(
                db_session,
                investigation_id=f"INV-PG{i:03d}",
                status="completed",
            )
        _seed(db_session, investigation_id="INV-PG-OTHER", status="running")
        db_session.commit()

        # First page
        result = repo.list_investigations(limit=2, offset=0, status="completed")
        assert len(result) == 2
        total = repo.count_investigations(status="completed")
        assert total == 5

        # Second page
        result2 = repo.list_investigations(limit=2, offset=2, status="completed")
        assert len(result2) == 2

        # Third page (only 1 left)
        result3 = repo.list_investigations(limit=2, offset=4, status="completed")
        assert len(result3) == 1

    def test_no_filters_returns_all(self, db_session, repo):
        _seed(db_session, investigation_id="INV-NF01")
        _seed(db_session, investigation_id="INV-NF02")
        db_session.commit()

        result = repo.list_investigations()
        assert len(result) == 2
        assert repo.count_investigations() == 2


# ===========================================================================
# Service — Filter tests
# ===========================================================================


class TestServiceFilters:
    """Tests for InvestigationHistoryService with filter parameters."""

    def test_investigation_id_filter(self, db_session, service):
        _seed(db_session, investigation_id="INV-SVC-A-001")
        _seed(db_session, investigation_id="INV-SVC-B-001")
        db_session.commit()

        result = service.list_investigations(
            db_session, investigation_id="SVC-A"
        )
        assert result.total == 1
        assert result.items[0].investigation_id == "INV-SVC-A-001"

    def test_status_filter(self, db_session, service):
        _seed(db_session, investigation_id="INV-SF01", status="completed")
        _seed(db_session, investigation_id="INV-SF02", status="running")
        db_session.commit()

        result = service.list_investigations(db_session, status="running")
        assert result.total == 1
        assert result.items[0].investigation_id == "INV-SF02"

    def test_merchant_filter(self, db_session, service):
        _seed(
            db_session,
            investigation_id="INV-MF01",
            merchant_filter="merchant_001",
        )
        _seed(
            db_session,
            investigation_id="INV-MF02",
            merchant_filter="merchant_002",
        )
        db_session.commit()

        result = service.list_investigations(
            db_session, merchant_filter="merchant_001"
        )
        assert result.total == 1
        assert result.items[0].investigation_id == "INV-MF01"

    def test_date_range_filter(self, db_session, service):
        base = datetime(2025, 8, 1, tzinfo=timezone.utc)
        r1 = _seed(db_session, investigation_id="INV-DR-S01")
        r1.created_at = base
        r2 = _seed(db_session, investigation_id="INV-DR-S02")
        r2.created_at = base + timedelta(days=5)
        r3 = _seed(db_session, investigation_id="INV-DR-S03")
        r3.created_at = base + timedelta(days=10)
        db_session.commit()

        result = service.list_investigations(
            db_session,
            created_from=base + timedelta(days=1),
            created_to=base + timedelta(days=8),
        )
        assert result.total == 1
        assert result.items[0].investigation_id == "INV-DR-S02"

    def test_combined_filters(self, db_session, service):
        base = datetime(2025, 8, 1, tzinfo=timezone.utc)
        r1 = _seed(
            db_session,
            investigation_id="INV-CB01",
            status="completed",
            merchant_filter="merchant_003",
        )
        r1.created_at = base
        r2 = _seed(
            db_session,
            investigation_id="INV-CB02",
            status="completed",
            merchant_filter="merchant_004",
        )
        r2.created_at = base
        _seed(
            db_session,
            investigation_id="INV-CB03",
            status="running",
            merchant_filter="merchant_003",
        )
        db_session.commit()

        result = service.list_investigations(
            db_session,
            status="completed",
            merchant_filter="merchant_003",
        )
        assert result.total == 1
        assert result.items[0].investigation_id == "INV-CB01"

    def test_empty_filters_returns_all(self, db_session, service):
        _seed(db_session, investigation_id="INV-EF01")
        _seed(db_session, investigation_id="INV-EF02")
        db_session.commit()

        result = service.list_investigations(db_session)
        assert result.total == 2

    def test_filtered_total_affects_pagination(self, db_session, service):
        for i in range(5):
            _seed(
                db_session,
                investigation_id=f"INV-PF{i:03d}",
                status="completed",
            )
        _seed(db_session, investigation_id="INV-PF-OTHER", status="running")
        db_session.commit()

        result = service.list_investigations(
            db_session, limit=2, offset=0, status="completed"
        )
        assert result.total == 5
        assert len(result.items) == 2

    def test_no_results_for_filter(self, db_session, service):
        _seed(db_session, investigation_id="INV-NR01", status="completed")
        db_session.commit()

        result = service.list_investigations(
            db_session, investigation_id="NONEXISTENT"
        )
        assert result.total == 0
        assert result.items == []


# ===========================================================================
# API — Filter tests
# ===========================================================================


@pytest.fixture()
def test_app(tmp_path):
    """Create a FastAPI app bound to a temporary SQLite database."""
    from fastapi.testclient import TestClient

    db_url = f"sqlite:///{tmp_path / 'test_filters.db'}"
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


def _seed_api(session, count=3, **overrides):
    """Seed test investigations via direct ORM inserts."""
    ids = []
    for i in range(count):
        inv_id = overrides.get("investigation_id_prefix", "INV-API") + f"-{i:03d}"
        data = dict(
            investigation_id=inv_id,
            status=overrides.get("status", "completed"),
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=2.0,
            min_history_days=3,
            merchant_filter=overrides.get("merchant_filter", None),
            total_results=100 + i,
            spikes_detected=10 + i,
            fraud_incidents=5 + i,
            organic_incidents=3 + i,
            review_required=2 + i,
            baseline_windows=90 - i,
            spike_rate=0.1 + i * 0.01,
            processing_note=f"Test {i}",
        )
        run = InvestigationRun(**data)
        session.add(run)
        session.flush()
        ids.append(run.investigation_id)
    session.commit()
    return ids


class TestAPIFilters:
    """API-level tests for investigation filtering."""

    def test_unfiltered_list_unchanged(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=3)

        response = client.get("/api/v1/investigations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_investigation_id_filter(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, investigation_id_prefix="INV-ACH")
        _seed_api(session, count=1, investigation_id_prefix="INV-BCH")
        session.commit()

        response = client.get("/api/v1/investigations?investigation_id=ACH")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["investigation_id"].startswith("INV-ACH")

    def test_status_filter(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, status="completed", investigation_id_prefix="INV-ST-C")
        _seed_api(session, count=1, status="running", investigation_id_prefix="INV-ST-R")

        response = client.get("/api/v1/investigations?status=running")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "running"

    def test_merchant_filter(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, merchant_filter="merchant_001", investigation_id_prefix="INV-MF-A")
        _seed_api(session, count=1, merchant_filter="merchant_002", investigation_id_prefix="INV-MF-B")

        response = client.get("/api/v1/investigations?merchant_filter=merchant_001")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_created_from_filter(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=2, investigation_id_prefix="INV-CF-API")
        session.commit()

        # Set one to old date, one to recent
        runs = session.query(InvestigationRun).all()
        runs[0].created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        runs[1].created_at = datetime(2025, 8, 1, tzinfo=timezone.utc)
        session.commit()

        response = client.get(
            "/api/v1/investigations?created_from=2025-06-01T00:00:00Z"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_created_to_filter(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=2, investigation_id_prefix="INV-CT-API")
        session.commit()

        runs = session.query(InvestigationRun).all()
        runs[0].created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        runs[1].created_at = datetime(2025, 8, 1, tzinfo=timezone.utc)
        session.commit()

        response = client.get(
            "/api/v1/investigations?created_to=2025-06-01T00:00:00Z"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_invalid_date_range(self, test_app):
        client, _, _ = test_app
        response = client.get(
            "/api/v1/investigations?created_from=2025-08-01T00:00:00Z&created_to=2025-01-01T00:00:00Z"
        )
        assert response.status_code == 422
        assert "created_from" in response.json()["detail"]

    def test_combined_filters(self, test_app):
        client, session, _ = test_app
        _seed_api(
            session, count=1, investigation_id_prefix="INV-CMB-A",
            status="completed", merchant_filter="merchant_001",
        )
        _seed_api(
            session, count=1, investigation_id_prefix="INV-CMB-B",
            status="completed", merchant_filter="merchant_002",
        )
        _seed_api(
            session, count=1, investigation_id_prefix="INV-OTH-A",
            status="running", merchant_filter="merchant_001",
        )

        response = client.get(
            "/api/v1/investigations?status=completed&merchant_filter=merchant_001"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "CMB-A" in data["items"][0]["investigation_id"]

    def test_filter_pagination_preserves_filters(self, test_app):
        client, session, _ = test_app
        for i in range(5):
            _seed_api(
                session, count=1,
                investigation_id_prefix=f"INV-PG{i}",
                status="completed",
            )
        _seed_api(session, count=1, investigation_id_prefix="INV-PG-X", status="running")
        session.commit()

        # Page 1
        r1 = client.get(
            "/api/v1/investigations?status=completed&limit=2&offset=0"
        ).json()
        assert r1["total"] == 5
        assert len(r1["items"]) == 2

        # Page 2
        r2 = client.get(
            "/api/v1/investigations?status=completed&limit=2&offset=2"
        ).json()
        assert r2["total"] == 5
        assert len(r2["items"]) == 2
        # Should not overlap with page 1
        ids1 = {i["investigation_id"] for i in r1["items"]}
        ids2 = {i["investigation_id"] for i in r2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_filter_total_reflects_results(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=3, status="completed", investigation_id_prefix="INV-FT-C")
        _seed_api(session, count=2, status="running", investigation_id_prefix="INV-FT-R")

        all_resp = client.get("/api/v1/investigations").json()
        completed_resp = client.get(
            "/api/v1/investigations?status=completed"
        ).json()

        assert all_resp["total"] == 5
        assert completed_resp["total"] == 3

    def test_empty_result_message(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, status="completed", investigation_id_prefix="INV-EM")

        response = client.get(
            "/api/v1/investigations?investigation_id=NONEXISTENT"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
