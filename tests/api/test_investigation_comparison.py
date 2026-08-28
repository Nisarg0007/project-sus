"""
Tests for investigation comparison endpoint.

Verifies:
- Validation: missing base_id, missing compare_id, same IDs
- 404 for nonexistent investigations
- Summary comparison: positive/negative/zero change, percentage, division by zero
- Incident comparison: only in base, only in compare, changed, unchanged
- API contract: no internal DB IDs, existing endpoints unchanged
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
    from fastapi.testclient import TestClient

    db_url = f"sqlite:///{tmp_path / 'test_compare.db'}"
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


def _seed(session, investigation_id, *, total_results=100, spikes_detected=10,
          fraud_incidents=5, organic_incidents=3, review_required=2,
          baseline_windows=90, spike_rate=0.1, incidents=None):
    """Seed a test investigation with optional incidents."""
    run = InvestigationRun(
        investigation_id=investigation_id,
        status="completed",
        transactions_path="data/raw/transactions.csv",
        window_labels_path="data/raw/window_labels.csv",
        z_threshold=2.0,
        min_history_days=3,
        total_results=total_results,
        spikes_detected=spikes_detected,
        fraud_incidents=fraud_incidents,
        organic_incidents=organic_incidents,
        review_required=review_required,
        baseline_windows=baseline_windows,
        spike_rate=spike_rate,
        processing_note="",
    )
    session.add(run)
    session.flush()

    for inc_data in (incidents or []):
        inc = PersistedIncident(
            investigation_run_id=run.id,
            incident_id=inc_data["incident_id"],
            merchant_id=inc_data.get("merchant_id", "merchant_001"),
            date="2025-07-24",
            severity=inc_data.get("severity", "critical"),
            status="open",
            classification=inc_data.get("classification", "fraud_spike"),
            predicted_cause=inc_data.get("predicted_cause"),
            fraud_probability=inc_data.get("fraud_probability", 0.9),
            confidence=inc_data.get("confidence", 0.8),
            confidence_band="high_confidence",
            anomaly_score=inc_data.get("anomaly_score", 3.0),
            decision_reason="",
            anomaly_summary="",
            top_signals_json=json.dumps(inc_data.get("top_signals", [])),
            recommended_action="",
        )
        session.add(inc)

    session.commit()
    return run


# ===========================================================================
# Validation tests
# ===========================================================================


class TestValidation:

    def test_missing_base_id(self, test_app):
        client, _, _ = test_app
        r = client.get("/api/v1/investigations/compare?compare_id=INV-B")
        assert r.status_code == 422

    def test_missing_compare_id(self, test_app):
        client, _, _ = test_app
        r = client.get("/api/v1/investigations/compare?base_id=INV-A")
        assert r.status_code == 422

    def test_same_ids(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-SAME")
        r = client.get("/api/v1/investigations/compare?base_id=INV-SAME&compare_id=INV-SAME")
        assert r.status_code == 422
        assert "must be different" in r.json()["detail"]

    def test_base_not_found(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-EXISTS")
        r = client.get("/api/v1/investigations/compare?base_id=INV-NOPE&compare_id=INV-EXISTS")
        assert r.status_code == 404
        assert "Base" in r.json()["detail"]

    def test_compare_not_found(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-EXISTS")
        r = client.get("/api/v1/investigations/compare?base_id=INV-EXISTS&compare_id=INV-NOPE")
        assert r.status_code == 404
        assert "Comparison" in r.json()["detail"]


# ===========================================================================
# Summary comparison tests
# ===========================================================================


class TestSummaryComparison:

    def test_positive_change(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-A1", total_results=100, spikes_detected=10)
        _seed(session, "INV-B1", total_results=150, spikes_detected=15)
        r = client.get("/api/v1/investigations/compare?base_id=INV-A1&compare_id=INV-B1")
        assert r.status_code == 200
        data = r.json()
        tr = data["summary"]["total_results"]
        assert tr["base_value"] == 100
        assert tr["compare_value"] == 150
        assert tr["absolute_change"] == 50
        assert tr["percentage_change"] == 50.0

    def test_negative_change(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-A2", fraud_incidents=20)
        _seed(session, "INV-B2", fraud_incidents=5)
        r = client.get("/api/v1/investigations/compare?base_id=INV-A2&compare_id=INV-B2")
        data = r.json()
        fi = data["summary"]["fraud_incidents"]
        assert fi["absolute_change"] == -15
        assert fi["percentage_change"] == -75.0

    def test_zero_change(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-A3", total_results=100)
        _seed(session, "INV-B3", total_results=100)
        r = client.get("/api/v1/investigations/compare?base_id=INV-A3&compare_id=INV-B3")
        data = r.json()
        tr = data["summary"]["total_results"]
        assert tr["absolute_change"] == 0
        assert tr["percentage_change"] == 0.0

    def test_division_by_zero(self, test_app):
        """When base is 0, percentage_change should be null."""
        client, session, _ = test_app
        _seed(session, "INV-A4", spikes_detected=0)
        _seed(session, "INV-B4", spikes_detected=10)
        r = client.get("/api/v1/investigations/compare?base_id=INV-A4&compare_id=INV-B4")
        data = r.json()
        sd = data["summary"]["spikes_detected"]
        assert sd["base_value"] == 0
        assert sd["compare_value"] == 10
        assert sd["absolute_change"] == 10
        assert sd["percentage_change"] is None

    def test_spike_rate_comparison(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-A5", spike_rate=0.1)
        _seed(session, "INV-B5", spike_rate=0.25)
        r = client.get("/api/v1/investigations/compare?base_id=INV-A5&compare_id=INV-B5")
        data = r.json()
        sr = data["summary"]["spike_rate"]
        assert sr["base_value"] == 0.1
        assert sr["compare_value"] == 0.25


# ===========================================================================
# Incident comparison tests
# ===========================================================================


class TestIncidentComparison:

    def test_incident_only_in_base(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-IB1", incidents=[
            {"incident_id": "INC-001", "merchant_id": "m1"},
        ])
        _seed(session, "INV-IC1", incidents=[])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB1&compare_id=INV-IC1")
        data = r.json()
        assert data["incidents"]["only_in_base"] == ["INC-001"]
        assert data["incidents"]["only_in_compare"] == []

    def test_incident_only_in_compare(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-IB2", incidents=[])
        _seed(session, "INV-IC2", incidents=[
            {"incident_id": "INC-002", "merchant_id": "m2"},
        ])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB2&compare_id=INV-IC2")
        data = r.json()
        assert data["incidents"]["only_in_compare"] == ["INC-002"]

    def test_incident_in_both_unchanged(self, test_app):
        client, session, _ = test_app
        inc = {"incident_id": "INC-003", "merchant_id": "m3", "severity": "critical",
               "classification": "fraud_spike", "fraud_probability": 0.9, "confidence": 0.8,
               "anomaly_score": 3.0, "predicted_cause": "payment_failure"}
        _seed(session, "INV-IB3", incidents=[inc])
        _seed(session, "INV-IC3", incidents=[inc.copy()])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB3&compare_id=INV-IC3")
        data = r.json()
        assert "INC-003" in data["incidents"]["in_both"]
        assert data["incidents"]["changed"] == []
        assert data["incidents"]["unchanged_count"] == 1

    def test_severity_change(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-IB4", incidents=[
            {"incident_id": "INC-004", "severity": "low"},
        ])
        _seed(session, "INV-IC4", incidents=[
            {"incident_id": "INC-004", "severity": "critical"},
        ])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB4&compare_id=INV-IC4")
        data = r.json()
        changed = data["incidents"]["changed"]
        assert len(changed) == 1
        assert changed[0]["incident_id"] == "INC-004"
        assert changed[0]["severity_changed"] is True
        assert changed[0]["old_severity"] == "low"
        assert changed[0]["new_severity"] == "critical"

    def test_classification_change(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-IB5", incidents=[
            {"incident_id": "INC-005", "classification": "organic_spike"},
        ])
        _seed(session, "INV-IC5", incidents=[
            {"incident_id": "INC-005", "classification": "fraud_spike"},
        ])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB5&compare_id=INV-IC5")
        data = r.json()
        ch = data["incidents"]["changed"][0]
        assert ch["classification_changed"] is True
        assert ch["old_classification"] == "organic_spike"
        assert ch["new_classification"] == "fraud_spike"

    def test_numeric_score_changes(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-IB6", incidents=[{
            "incident_id": "INC-006", "fraud_probability": 0.5, "confidence": 0.6, "anomaly_score": 2.0,
        }])
        _seed(session, "INV-IC6", incidents=[{
            "incident_id": "INC-006", "fraud_probability": 0.9, "confidence": 0.7, "anomaly_score": 3.5,
        }])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB6&compare_id=INV-IC6")
        data = r.json()
        ch = data["incidents"]["changed"][0]
        assert ch["fraud_probability_changed"] is True
        assert ch["old_fraud_probability"] == 0.5
        assert ch["new_fraud_probability"] == 0.9
        assert ch["confidence_changed"] is True
        assert ch["anomaly_score_changed"] is True

    def test_multiple_simultaneous_changes(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-IB7", incidents=[{
            "incident_id": "INC-007", "severity": "low", "classification": "baseline",
            "fraud_probability": 0.1, "confidence": 0.3, "anomaly_score": 0.5,
            "predicted_cause": "organic_demand",
        }])
        _seed(session, "INV-IC7", incidents=[{
            "incident_id": "INC-007", "severity": "critical", "classification": "fraud_spike",
            "fraud_probability": 0.95, "confidence": 0.9, "anomaly_score": 4.0,
            "predicted_cause": "payment_failure",
        }])
        r = client.get("/api/v1/investigations/compare?base_id=INV-IB7&compare_id=INV-IC7")
        data = r.json()
        ch = data["incidents"]["changed"][0]
        assert ch["severity_changed"]
        assert ch["classification_changed"]
        assert ch["fraud_probability_changed"]
        assert ch["confidence_changed"]
        assert ch["anomaly_score_changed"]
        assert ch["predicted_cause_changed"]


# ===========================================================================
# API contract tests
# ===========================================================================


class TestAPIContract:

    def test_no_internal_db_ids(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-NC1", incidents=[
            {"incident_id": "INC-NC1"},
        ])
        _seed(session, "INV-NC2", incidents=[
            {"incident_id": "INC-NC2"},
        ])
        r = client.get("/api/v1/investigations/compare?base_id=INV-NC1&compare_id=INV-NC2")
        data = r.json()
        # Response should not contain "id" (numeric PK) fields
        assert "id" not in data["base"]
        assert "id" not in data["compare"]
        assert data["base"]["investigation_id"] == "INV-NC1"
        assert data["compare"]["investigation_id"] == "INV-NC2"

    def test_existing_endpoints_unchanged(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-EX1")
        # History list
        r = client.get("/api/v1/investigations")
        assert r.status_code == 200
        # Detail
        r = client.get("/api/v1/investigations/INV-EX1")
        assert r.status_code == 200
        # Compare
        _seed(session, "INV-EX2")
        r = client.get("/api/v1/investigations/compare?base_id=INV-EX1&compare_id=INV-EX2")
        assert r.status_code == 200

    def test_response_shape(self, test_app):
        client, session, _ = test_app
        _seed(session, "INV-SH1", incidents=[{"incident_id": "INC-SH1"}])
        _seed(session, "INV-SH2", incidents=[{"incident_id": "INC-SH2", "severity": "high"}])
        r = client.get("/api/v1/investigations/compare?base_id=INV-SH1&compare_id=INV-SH2")
        data = r.json()

        # Top-level keys
        assert set(data.keys()) == {"base", "compare", "summary", "incidents"}

        # Base/compare metadata
        for meta in (data["base"], data["compare"]):
            assert "investigation_id" in meta
            assert "created_at" in meta
            assert "status" in meta

        # Summary has all expected metrics
        expected_metrics = {
            "total_results", "spikes_detected", "fraud_incidents",
            "organic_incidents", "review_required", "baseline_windows", "spike_rate",
        }
        assert set(data["summary"].keys()) == expected_metrics
        for metric in data["summary"].values():
            assert "label" in metric
            assert "base_value" in metric
            assert "compare_value" in metric
            assert "absolute_change" in metric
            assert "percentage_change" in metric

        # Incidents
        inc = data["incidents"]
        assert "only_in_base" in inc
        assert "only_in_compare" in inc
        assert "in_both" in inc
        assert "changed" in inc
        assert "unchanged_count" in inc
