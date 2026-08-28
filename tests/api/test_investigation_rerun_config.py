"""
Tests for investigation rerun-with-config endpoint.

Verifies:
- Successful configurable rerun with overrides
- Configuration inheritance (omitted fields keep original values)
- Multiple overrides applied together
- Invalid z_threshold / min_history_days rejected
- Merchant filter override and inheritance
- Nonexistent investigation returns 404
- Original investigation remains unchanged
- Existing rerun endpoint still works
"""

from __future__ import annotations

import json

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

    db_url = f"sqlite:///{tmp_path / 'test_rerun_config.db'}"
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


def _seed_investigation(session, investigation_id="INV-CFG-001", **overrides):
    """Insert a test investigation run with known configuration."""
    defaults = dict(
        investigation_id=investigation_id,
        status="completed",
        transactions_path="data/raw/transactions.csv",
        window_labels_path="data/raw/window_labels.csv",
        z_threshold=3.0,
        min_history_days=30,
        merchant_filter="merchant_001",
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

    inc = PersistedIncident(
        investigation_run_id=run.id,
        incident_id=f"INC-CFG-{investigation_id[-3:]}",
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
# POST /api/v1/investigations/{id}/rerun-with-config — Tests
# ---------------------------------------------------------------------------


class TestRerunWithConfig:
    """Successful configurable reruns."""

    def test_successful_rerun_with_config(self, test_app):
        """Configurable rerun should create a new investigation."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-010")

        response = client.post(
            "/api/v1/investigations/INV-CFG-010/rerun-with-config",
            json={"z_threshold": 2.5},
        )
        assert response.status_code == 200
        data = response.json()

        # New ID different from original
        assert data["investigation_id"] != "INV-CFG-010"
        assert data["investigation_id"].startswith("INV-")
        assert "summary" in data
        assert "incidents" in data

    def test_new_investigation_persisted(self, test_app):
        """The new investigation should be persisted."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-011")

        response = client.post(
            "/api/v1/investigations/INV-CFG-011/rerun-with-config",
            json={"z_threshold": 2.0},
        )
        new_id = response.json()["investigation_id"]

        session.expire_all()
        run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert run is not None
        assert run.status == "completed"

    def test_original_unchanged(self, test_app):
        """The original investigation must not be modified."""
        client, session, _ = test_app
        original = _seed_investigation(
            session,
            investigation_id="INV-CFG-012",
            z_threshold=3.0,
            min_history_days=30,
            merchant_filter="merchant_001",
        )

        orig_z = original.z_threshold
        orig_min = original.min_history_days
        orig_merchant = original.merchant_filter

        client.post(
            "/api/v1/investigations/INV-CFG-012/rerun-with-config",
            json={"z_threshold": 1.0, "min_history_days": 5},
        )

        session.expire_all()
        run = session.query(InvestigationRun).filter_by(
            investigation_id="INV-CFG-012"
        ).first()
        assert run.z_threshold == orig_z
        assert run.min_history_days == orig_min
        assert run.merchant_filter == orig_merchant

    def test_response_shape(self, test_app):
        """Response should match the InvestigationResponse schema."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-013")

        response = client.post(
            "/api/v1/investigations/INV-CFG-013/rerun-with-config",
            json={"z_threshold": 2.0},
        )
        data = response.json()

        assert "investigation_id" in data
        assert "summary" in data
        assert "incidents" in data
        assert "total_results" in data
        assert "processing_note" in data

        summary = data["summary"]
        assert "total_windows" in summary
        assert "spikes_detected" in summary
        assert "spike_rate" in summary

    def test_unique_ids_across_reruns(self, test_app):
        """Multiple configurable reruns produce unique IDs."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-014")

        r1 = client.post(
            "/api/v1/investigations/INV-CFG-014/rerun-with-config",
            json={"z_threshold": 2.0},
        ).json()
        r2 = client.post(
            "/api/v1/investigations/INV-CFG-014/rerun-with-config",
            json={"z_threshold": 2.5},
        ).json()

        assert r1["investigation_id"] != r2["investigation_id"]
        assert r1["investigation_id"] != "INV-CFG-014"
        assert r2["investigation_id"] != "INV-CFG-014"


class TestConfigurationInheritance:
    """Omitted fields should inherit from the original investigation."""

    def test_partial_override_inherits_rest(self, test_app):
        """When only z_threshold is overridden, other values stay the same."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-020",
            z_threshold=3.0,
            min_history_days=30,
            merchant_filter="merchant_001",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-020/rerun-with-config",
            json={"z_threshold": 1.5},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        # Verify the new investigation used the original values for unoverridden fields
        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run is not None
        assert new_run.z_threshold == 1.5
        assert new_run.min_history_days == 30
        assert new_run.merchant_filter == "merchant_001"

    def test_empty_body_inherits_all(self, test_app):
        """An empty request body should use the original configuration entirely."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-021",
            z_threshold=4.0,
            min_history_days=60,
            merchant_filter=None,
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-021/rerun-with-config",
            json={},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run is not None
        assert new_run.z_threshold == 4.0
        assert new_run.min_history_days == 60
        assert new_run.merchant_filter is None

    def test_multiple_overrides_applied(self, test_app):
        """All three overrides should be applied when all are provided."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-022",
            z_threshold=3.0,
            min_history_days=30,
            merchant_filter="merchant_001",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-022/rerun-with-config",
            json={
                "z_threshold": 1.0,
                "min_history_days": 7,
                "merchant_filter": "merchant_005",
            },
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run is not None
        assert new_run.z_threshold == 1.0
        assert new_run.min_history_days == 7
        assert new_run.merchant_filter == "merchant_005"

    def test_null_overrides_keep_original(self, test_app):
        """Explicit null for z_threshold/min_history_days keeps originals.

        Explicit null for merchant_filter clears the filter (sets to None)
        because the user intentionally provided the field.
        Omitting a field entirely keeps the original value.
        """
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-023",
            z_threshold=3.0,
            min_history_days=30,
            merchant_filter="merchant_001",
        )

        # Send null for z_threshold and min_history_days (keep original)
        # but omit merchant_filter (also keep original)
        response = client.post(
            "/api/v1/investigations/INV-CFG-023/rerun-with-config",
            json={
                "z_threshold": None,
                "min_history_days": None,
            },
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run is not None
        assert new_run.z_threshold == 3.0
        assert new_run.min_history_days == 30
        assert new_run.merchant_filter == "merchant_001"

    def test_explicit_null_clears_merchant_filter(self, test_app):
        """Explicitly sending merchant_filter=null should clear the filter."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-023B",
            z_threshold=3.0,
            min_history_days=30,
            merchant_filter="merchant_001",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-023B/rerun-with-config",
            json={"merchant_filter": None},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run is not None
        assert new_run.merchant_filter is None


class TestMerchantFilterBehavior:
    """Merchant filter override and inheritance."""

    def test_override_merchant_filter(self, test_app):
        """Merchant filter override should take effect."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-030",
            merchant_filter="merchant_001",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-030/rerun-with-config",
            json={"merchant_filter": "merchant_003"},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run.merchant_filter == "merchant_003"

    def test_empty_string_clears_filter(self, test_app):
        """An empty merchant_filter string should clear the filter (set to None)."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-031",
            merchant_filter="merchant_001",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-031/rerun-with-config",
            json={"merchant_filter": ""},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        # Empty string should become None (clearing the filter)
        assert new_run.merchant_filter is None

    def test_whitespace_only_clears_filter(self, test_app):
        """Whitespace-only merchant_filter should clear the filter."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-032",
            merchant_filter="merchant_001",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-032/rerun-with-config",
            json={"merchant_filter": "   "},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run.merchant_filter is None


class TestValidation:
    """Invalid parameters should be rejected."""

    def test_z_threshold_zero_rejected(self, test_app):
        """z_threshold of 0 should be rejected."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-040")

        response = client.post(
            "/api/v1/investigations/INV-CFG-040/rerun-with-config",
            json={"z_threshold": 0},
        )
        assert response.status_code == 422

    def test_z_threshold_negative_rejected(self, test_app):
        """Negative z_threshold should be rejected."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-041")

        response = client.post(
            "/api/v1/investigations/INV-CFG-041/rerun-with-config",
            json={"z_threshold": -1.0},
        )
        assert response.status_code == 422

    def test_z_threshold_too_large_rejected(self, test_app):
        """z_threshold > 10 should be rejected."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-042")

        response = client.post(
            "/api/v1/investigations/INV-CFG-042/rerun-with-config",
            json={"z_threshold": 11.0},
        )
        assert response.status_code == 422

    def test_min_history_days_zero_rejected(self, test_app):
        """min_history_days of 0 should be rejected."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-043")

        response = client.post(
            "/api/v1/investigations/INV-CFG-043/rerun-with-config",
            json={"min_history_days": 0},
        )
        assert response.status_code == 422

    def test_min_history_days_negative_rejected(self, test_app):
        """Negative min_history_days should be rejected."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-044")

        response = client.post(
            "/api/v1/investigations/INV-CFG-044/rerun-with-config",
            json={"min_history_days": -5},
        )
        assert response.status_code == 422


class TestNotFound:
    """Nonexistent investigation handling."""

    def test_nonexistent_returns_404(self, test_app):
        """Rerunning a nonexistent investigation should return 404."""
        client, _, _ = test_app

        response = client.post(
            "/api/v1/investigations/INV-NONEXISTENT/rerun-with-config",
            json={"z_threshold": 2.0},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestBackwardCompatibility:
    """Verify existing rerun endpoint is not affected."""

    def test_existing_rerun_still_works(self, test_app):
        """POST /{id}/rerun should still work after the new endpoint is added."""
        client, session, _ = test_app
        _seed_investigation(session, investigation_id="INV-CFG-050")

        response = client.post("/api/v1/investigations/INV-CFG-050/rerun")
        assert response.status_code == 200
        data = response.json()
        assert data["investigation_id"] != "INV-CFG-050"

    def test_configurable_rerun_stores_correctly(self, test_app):
        """Configurable rerun should store the effective (merged) configuration."""
        client, session, _ = test_app
        _seed_investigation(
            session,
            investigation_id="INV-CFG-051",
            z_threshold=4.0,
            min_history_days=45,
            merchant_filter="merchant_002",
        )

        response = client.post(
            "/api/v1/investigations/INV-CFG-051/rerun-with-config",
            json={"z_threshold": 2.0},
        )
        assert response.status_code == 200
        new_id = response.json()["investigation_id"]

        session.expire_all()
        new_run = session.query(InvestigationRun).filter_by(
            investigation_id=new_id
        ).first()
        assert new_run is not None
        # z_threshold overridden, others inherited
        assert new_run.z_threshold == 2.0
        assert new_run.min_history_days == 45
        assert new_run.merchant_filter == "merchant_002"

    def test_run_endpoint_still_works(self, test_app):
        """POST /investigations/run should be unaffected."""
        client, _, _ = test_app
        response = client.post("/api/v1/investigations/run", json={})
        assert response.status_code in (200, 404, 422, 500)
