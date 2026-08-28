"""
Tests for investigation history sorting.

Verifies:
- Default ordering (created_at DESC)
- Sort by each supported column
- Ascending and descending directions
- Deterministic secondary ordering (investigation_id DESC)
- Interaction with filters
- Pagination after sorting
- Invalid sort_by values return 422
- Invalid sort_order values return 422
- Backward-compatible unsorted requests
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import InvestigationRun
from src.repositories.investigation_repository import InvestigationRepository
from src.services.investigation_history_service import InvestigationHistoryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
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

_BASE = dict(
    investigation_id="INV-TEST001",
    status="completed",
    transactions_path="data/raw/transactions.csv",
    window_labels_path="data/raw/window_labels.csv",
    z_threshold=2.0,
    min_history_days=3,
    total_results=100,
    spikes_detected=10,
    fraud_incidents=5,
    organic_incidents=3,
    review_required=2,
    baseline_windows=90,
    spike_rate=0.1,
    processing_note="",
)


def _seed(session, **overrides):
    data = {**_BASE, **overrides}
    run = InvestigationRun(**data)
    session.add(run)
    session.flush()
    return run


def _seed_with_values(session, *, investigation_id, created_at=None, **field_overrides):
    """Seed a run with specific values for sort testing."""
    data = {
        **_BASE,
        "investigation_id": investigation_id,
        **field_overrides,
    }
    run = InvestigationRun(**data)
    session.add(run)
    session.flush()
    if created_at:
        run.created_at = created_at
        session.flush()
    return run


# ===========================================================================
# Repository — Sorting tests
# ===========================================================================


class TestRepositorySorting:
    """Tests for InvestigationRepository._apply_sorting and sorted queries."""

    def test_default_ordering_newest_first(self, db_session, repo):
        """Default ordering should be created_at DESC."""
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(db_session, investigation_id="INV-OLD", created_at=base)
        _seed_with_values(db_session, investigation_id="INV-NEW", created_at=base + timedelta(days=5))
        _seed_with_values(db_session, investigation_id="INV-MID", created_at=base + timedelta(days=2))
        db_session.commit()

        result = repo.list_investigations()
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-NEW", "INV-MID", "INV-OLD"]

    def test_deterministic_secondary_ordering(self, db_session, repo):
        """Same created_at should break ties by investigation_id DESC."""
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(db_session, investigation_id="INV-C", created_at=base)
        _seed_with_values(db_session, investigation_id="INV-A", created_at=base)
        _seed_with_values(db_session, investigation_id="INV-B", created_at=base)
        db_session.commit()

        result = repo.list_investigations()
        ids = [r.investigation_id for r in result]
        # investigation_id DESC secondary order
        assert ids == ["INV-C", "INV-B", "INV-A"]

    def test_sort_by_total_results_desc(self, db_session, repo):
        _seed(db_session, investigation_id="INV-T1", total_results=50)
        _seed(db_session, investigation_id="INV-T2", total_results=200)
        _seed(db_session, investigation_id="INV-T3", total_results=100)
        db_session.commit()

        result = repo.list_investigations(sort_by="total_results", sort_order="desc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-T2", "INV-T3", "INV-T1"]

    def test_sort_by_total_results_asc(self, db_session, repo):
        _seed(db_session, investigation_id="INV-T1", total_results=50)
        _seed(db_session, investigation_id="INV-T2", total_results=200)
        _seed(db_session, investigation_id="INV-T3", total_results=100)
        db_session.commit()

        result = repo.list_investigations(sort_by="total_results", sort_order="asc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-T1", "INV-T3", "INV-T2"]

    def test_sort_by_spikes_detected(self, db_session, repo):
        _seed(db_session, investigation_id="INV-S1", spikes_detected=5)
        _seed(db_session, investigation_id="INV-S2", spikes_detected=50)
        _seed(db_session, investigation_id="INV-S3", spikes_detected=25)
        db_session.commit()

        result = repo.list_investigations(sort_by="spikes_detected", sort_order="desc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-S2", "INV-S3", "INV-S1"]

    def test_sort_by_fraud_incidents(self, db_session, repo):
        _seed(db_session, investigation_id="INV-F1", fraud_incidents=0)
        _seed(db_session, investigation_id="INV-F2", fraud_incidents=31)
        _seed(db_session, investigation_id="INV-F3", fraud_incidents=12)
        db_session.commit()

        result = repo.list_investigations(sort_by="fraud_incidents", sort_order="asc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-F1", "INV-F3", "INV-F2"]

    def test_sort_by_spike_rate(self, db_session, repo):
        _seed(db_session, investigation_id="INV-R1", spike_rate=0.05)
        _seed(db_session, investigation_id="INV-R2", spike_rate=0.50)
        _seed(db_session, investigation_id="INV-R3", spike_rate=0.20)
        db_session.commit()

        result = repo.list_investigations(sort_by="spike_rate", sort_order="desc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-R2", "INV-R3", "INV-R1"]

    def test_sort_by_created_at_asc(self, db_session, repo):
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(db_session, investigation_id="INV-A1", created_at=base)
        _seed_with_values(db_session, investigation_id="INV-A2", created_at=base + timedelta(days=2))
        _seed_with_values(db_session, investigation_id="INV-A3", created_at=base + timedelta(days=1))
        db_session.commit()

        result = repo.list_investigations(sort_by="created_at", sort_order="asc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-A1", "INV-A3", "INV-A2"]

    def test_invalid_sort_by_ignored(self, db_session, repo):
        """Invalid sort_by should fall back to default ordering."""
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(db_session, investigation_id="INV-X1", created_at=base)
        _seed_with_values(db_session, investigation_id="INV-X2", created_at=base + timedelta(days=1))
        db_session.commit()

        result = repo.list_investigations(sort_by="nonexistent_column", sort_order="desc")
        ids = [r.investigation_id for r in result]
        # Default: newest first
        assert ids == ["INV-X2", "INV-X1"]

    def test_sort_with_filter(self, db_session, repo):
        """Sorting should work correctly with active filters."""
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(
            db_session, investigation_id="INV-SF1",
            status="completed", total_results=50, created_at=base,
        )
        _seed_with_values(
            db_session, investigation_id="INV-SF2",
            status="completed", total_results=200, created_at=base + timedelta(days=1),
        )
        _seed_with_values(
            db_session, investigation_id="INV-SF3",
            status="running", total_results=300, created_at=base + timedelta(days=2),
        )
        db_session.commit()

        result = repo.list_investigations(
            status="completed",
            sort_by="total_results",
            sort_order="desc",
        )
        ids = [r.investigation_id for r in result]
        assert len(ids) == 2
        assert ids == ["INV-SF2", "INV-SF1"]

    def test_sort_with_pagination(self, db_session, repo):
        """Sorting + pagination should produce consistent pages."""
        for i in range(6):
            _seed(db_session, investigation_id=f"INV-PG{i:03d}", total_results=i * 10)
        db_session.commit()

        page1 = repo.list_investigations(limit=3, offset=0, sort_by="total_results", sort_order="desc")
        page2 = repo.list_investigations(limit=3, offset=3, sort_by="total_results", sort_order="desc")

        assert len(page1) == 3
        assert len(page2) == 3

        # Page 1 should have the highest values
        assert page1[0].total_results > page1[1].total_results
        # No overlap
        ids1 = {r.investigation_id for r in page1}
        ids2 = {r.investigation_id for r in page2}
        assert ids1.isdisjoint(ids2)

    def test_sort_deterministic_tie_breaking(self, db_session, repo):
        """Same total_results should break ties by investigation_id DESC."""
        _seed(db_session, investigation_id="INV-Z1", total_results=100)
        _seed(db_session, investigation_id="INV-Z2", total_results=100)
        _seed(db_session, investigation_id="INV-Z3", total_results=100)
        db_session.commit()

        result = repo.list_investigations(sort_by="total_results", sort_order="desc")
        ids = [r.investigation_id for r in result]
        assert ids == ["INV-Z3", "INV-Z2", "INV-Z1"]


# ===========================================================================
# Service — Sorting tests
# ===========================================================================


class TestServiceSorting:

    def test_default_sorting(self, db_session, service):
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(db_session, investigation_id="INV-SD1", created_at=base)
        _seed_with_values(db_session, investigation_id="INV-SD2", created_at=base + timedelta(days=1))
        db_session.commit()

        result = service.list_investigations(db_session)
        assert result.items[0].investigation_id == "INV-SD2"

    def test_sort_by_total_results(self, db_session, service):
        _seed(db_session, investigation_id="INV-ST1", total_results=50)
        _seed(db_session, investigation_id="INV-ST2", total_results=200)
        db_session.commit()

        result = service.list_investigations(
            db_session, sort_by="total_results", sort_order="desc"
        )
        assert result.items[0].investigation_id == "INV-ST2"

    def test_sort_with_filter_through_service(self, db_session, service):
        base = datetime(2025, 7, 1, tzinfo=timezone.utc)
        _seed_with_values(
            db_session, investigation_id="INV-SS1",
            status="completed", total_results=50, created_at=base,
        )
        _seed_with_values(
            db_session, investigation_id="INV-SS2",
            status="completed", total_results=200, created_at=base + timedelta(days=1),
        )
        db_session.commit()

        result = service.list_investigations(
            db_session,
            status="completed",
            sort_by="total_results",
            sort_order="asc",
        )
        assert result.items[0].investigation_id == "INV-SS1"


# ===========================================================================
# API — Sorting tests
# ===========================================================================


@pytest.fixture()
def test_app(tmp_path):
    from fastapi.testclient import TestClient

    db_url = f"sqlite:///{tmp_path / 'test_sort.db'}"
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


def _seed_api(session, count=3, prefix="INV-SRT", **overrides):
    ids = []
    for i in range(count):
        run = InvestigationRun(
            investigation_id=f"{prefix}-{i:03d}",
            status=overrides.get("status", "completed"),
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=2.0,
            min_history_days=3,
            total_results=overrides.get("total_results", 100 + i),
            spikes_detected=overrides.get("spikes_detected", 10 + i),
            fraud_incidents=overrides.get("fraud_incidents", 5 + i),
            organic_incidents=3 + i,
            review_required=2 + i,
            baseline_windows=90 - i,
            spike_rate=overrides.get("spike_rate", 0.1 + i * 0.01),
            processing_note=f"Test {i}",
        )
        session.add(run)
        session.flush()
        ids.append(run.investigation_id)
    session.commit()
    return ids


class TestAPISorting:

    def test_default_sorting(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=3, prefix="INV-DF")
        response = client.get("/api/v1/investigations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_sort_by_total_results_desc(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, prefix="INV-TD1", total_results=50)
        _seed_api(session, count=1, prefix="INV-TD2", total_results=200)
        _seed_api(session, count=1, prefix="INV-TD3", total_results=100)

        response = client.get("/api/v1/investigations?sort_by=total_results&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        ids = [i["investigation_id"] for i in data["items"]]
        assert ids[0].startswith("INV-TD2")  # 200 is highest

    def test_sort_by_total_results_asc(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, prefix="INV-TA1", total_results=50)
        _seed_api(session, count=1, prefix="INV-TA2", total_results=200)
        _seed_api(session, count=1, prefix="INV-TA3", total_results=100)

        response = client.get("/api/v1/investigations?sort_by=total_results&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        ids = [i["investigation_id"] for i in data["items"]]
        assert ids[0].startswith("INV-TA1")  # 50 is lowest

    def test_sort_by_spikes_detected(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, prefix="INV-SD1", spikes_detected=5)
        _seed_api(session, count=1, prefix="INV-SD2", spikes_detected=50)

        response = client.get("/api/v1/investigations?sort_by=spikes_detected&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        ids = [i["investigation_id"] for i in data["items"]]
        assert ids[0].startswith("INV-SD2")

    def test_sort_by_fraud_incidents(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, prefix="INV-FI1", fraud_incidents=0)
        _seed_api(session, count=1, prefix="INV-FI2", fraud_incidents=31)

        response = client.get("/api/v1/investigations?sort_by=fraud_incidents&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        ids = [i["investigation_id"] for i in data["items"]]
        assert ids[0].startswith("INV-FI2")

    def test_sort_by_spike_rate(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, prefix="INV-SR1", spike_rate=0.05)
        _seed_api(session, count=1, prefix="INV-SR2", spike_rate=0.50)

        response = client.get("/api/v1/investigations?sort_by=spike_rate&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        ids = [i["investigation_id"] for i in data["items"]]
        assert ids[0].startswith("INV-SR2")

    def test_invalid_sort_by_returns_422(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations?sort_by=nonexistent")
        assert response.status_code == 422
        assert "sort_by" in response.json()["detail"].lower()

    def test_invalid_sort_order_returns_422(self, test_app):
        client, _, _ = test_app
        response = client.get("/api/v1/investigations?sort_order=random")
        assert response.status_code == 422
        assert "sort_order" in response.json()["detail"].lower()

    def test_sort_with_filter(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=1, prefix="INV-SF1", status="completed", total_results=50)
        _seed_api(session, count=1, prefix="INV-SF2", status="completed", total_results=200)
        _seed_api(session, count=1, prefix="INV-SF3", status="running", total_results=300)

        response = client.get(
            "/api/v1/investigations?status=completed&sort_by=total_results&sort_order=desc"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        ids = [i["investigation_id"] for i in data["items"]]
        assert ids[0].startswith("INV-SF2")

    def test_sort_with_pagination(self, test_app):
        client, session, _ = test_app
        _seed_api(session, count=5, prefix="INV-SP", total_results=10)
        _seed_api(session, count=5, prefix="INV-SPB", total_results=200)

        r1 = client.get("/api/v1/investigations?sort_by=total_results&sort_order=desc&limit=3&offset=0").json()
        r2 = client.get("/api/v1/investigations?sort_by=total_results&sort_order=desc&limit=3&offset=3").json()

        assert r1["total"] == 10
        assert len(r1["items"]) == 3
        assert len(r2["items"]) == 3
        ids1 = {i["investigation_id"] for i in r1["items"]}
        ids2 = {i["investigation_id"] for i in r2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_backward_compatible_no_sort_params(self, test_app):
        """Existing requests without sort params should behave identically."""
        client, session, _ = test_app
        _seed_api(session, count=3, prefix="INV-BC")

        response = client.get("/api/v1/investigations?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
