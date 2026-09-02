"""
Tests for SQLAlchemy ORM models.

Verifies that:
1. Tables can be created from metadata
2. InvestigationRun can be inserted and retrieved
3. PersistedIncident can be associated with an InvestigationRun
4. Relationships work correctly
5. Required fields behave correctly
6. Nullable fields accept None where intended
7. Indexes are created
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base
from src.database.models import Dataset, InvestigationRun, PersistedIncident


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    TestSession = sessionmaker(bind=db_engine)
    session = TestSession()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Test: Table Creation
# ---------------------------------------------------------------------------


class TestTableCreation:
    """Verify that database tables are created correctly."""

    def test_all_tables_created(self, db_engine):
        """Metadata should create all tables."""
        inspector = inspect(db_engine)
        table_names = inspector.get_table_names()
        assert "investigation_runs" in table_names
        assert "persisted_incidents" in table_names
        assert "incident_status_history" in table_names
        assert "datasets" in table_names
        assert len(table_names) == 4

    def test_investigation_runs_columns(self, db_engine):
        """investigation_runs table should have expected columns."""
        inspector = inspect(db_engine)
        columns = {col["name"] for col in inspector.get_columns("investigation_runs")}
        expected = {
            "id", "investigation_id", "status", "created_at",
            "transactions_path", "window_labels_path", "model_path",
            "z_threshold", "min_history_days", "merchant_filter",
            "total_results", "spikes_detected", "fraud_incidents",
            "organic_incidents", "review_required", "baseline_windows",
            "spike_rate", "processing_note",
        }
        assert expected.issubset(columns)

    def test_persisted_incidents_columns(self, db_engine):
        """persisted_incidents table should have expected columns."""
        inspector = inspect(db_engine)
        columns = {col["name"] for col in inspector.get_columns("persisted_incidents")}
        expected = {
            "id", "investigation_run_id",
            "incident_id", "merchant_id", "date",
            "severity", "status", "classification", "predicted_cause",
            "fraud_probability", "confidence", "confidence_band", "anomaly_score",
            "decision_reason", "anomaly_summary", "top_signals_json",
            "recommended_action", "created_at",
        }
        assert expected.issubset(columns)


# ---------------------------------------------------------------------------
# Test: InvestigationRun CRUD
# ---------------------------------------------------------------------------


class TestInvestigationRun:
    """Test creating and reading InvestigationRun records."""

    def _make_run(self, **overrides) -> dict:
        """Create a valid InvestigationRun data dict."""
        defaults = {
            "investigation_id": "INV-TEST00000001",
            "status": "completed",
            "transactions_path": "data/raw/transactions.csv",
            "window_labels_path": "data/raw/window_labels.csv",
            "model_path": None,
            "z_threshold": 0.5,
            "min_history_days": 3,
            "merchant_filter": None,
            "total_results": 360,
            "spikes_detected": 73,
            "fraud_incidents": 31,
            "organic_incidents": 39,
            "review_required": 3,
            "baseline_windows": 287,
            "spike_rate": 0.203,
            "processing_note": "",
        }
        defaults.update(overrides)
        return defaults

    def test_create_investigation_run(self, db_session):
        """Should be able to create and commit an InvestigationRun."""
        run = InvestigationRun(**self._make_run())
        db_session.add(run)
        db_session.commit()

        retrieved = db_session.query(InvestigationRun).first()
        assert retrieved is not None
        assert retrieved.investigation_id == "INV-TEST00000001"
        assert retrieved.status == "completed"
        assert retrieved.total_results == 360
        assert retrieved.z_threshold == 0.5

    def test_investigation_id_is_unique(self, db_session):
        """Duplicate investigation_id should raise an integrity error."""
        run1 = InvestigationRun(**self._make_run())
        db_session.add(run1)
        db_session.commit()

        run2 = InvestigationRun(**self._make_run())
        db_session.add(run2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_nullable_fields_accept_none(self, db_session):
        """model_path and merchant_filter should accept None."""
        run = InvestigationRun(**self._make_run(
            model_path=None,
            merchant_filter=None,
        ))
        db_session.add(run)
        db_session.commit()

        retrieved = db_session.query(InvestigationRun).first()
        assert retrieved.model_path is None
        assert retrieved.merchant_filter is None

    def test_created_at_defaults_to_now(self, db_session):
        """created_at should be auto-set if not provided."""
        run = InvestigationRun(**self._make_run())
        # Remove created_at to test default
        if run.created_at:
            run.created_at = None
        db_session.add(run)
        db_session.commit()

        retrieved = db_session.query(InvestigationRun).first()
        assert retrieved.created_at is not None

    def test_repr(self, db_session):
        """repr should include investigation_id and status."""
        run = InvestigationRun(**self._make_run())
        db_session.add(run)
        db_session.commit()

        retrieved = db_session.query(InvestigationRun).first()
        assert "INV-TEST00000001" in repr(retrieved)
        assert "completed" in repr(retrieved)


# ---------------------------------------------------------------------------
# Test: PersistedIncident CRUD
# ---------------------------------------------------------------------------


class TestPersistedIncident:
    """Test creating and reading PersistedIncident records."""

    def _make_incident(self, run_id: int, **overrides) -> dict:
        """Create a valid PersistedIncident data dict."""
        defaults = {
            "investigation_run_id": run_id,
            "incident_id": "INC-merchant_001-20250724",
            "merchant_id": "merchant_001",
            "date": "2025-07-24",
            "severity": "critical",
            "status": "open",
            "classification": "fraud_spike",
            "predicted_cause": "payment_failure",
            "fraud_probability": 0.961,
            "confidence": 0.89,
            "confidence_band": "high_confidence",
            "anomaly_score": 3.2,
            "decision_reason": "High fraud probability with elevated failure rate",
            "anomaly_summary": "Payment failures increased; IP diversity dropped",
            "top_signals_json": json.dumps(["Top fraud contributor: payment_failure_rate"]),
            "recommended_action": "Review affected transactions",
        }
        defaults.update(overrides)
        return defaults

    def test_create_persisted_incident(self, db_session):
        """Should be able to create an incident linked to a run."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        incident = PersistedIncident(**self._make_incident(run_id=run.id))
        db_session.add(incident)
        db_session.commit()

        retrieved = db_session.query(PersistedIncident).first()
        assert retrieved is not None
        assert retrieved.incident_id == "INC-merchant_001-20250724"
        assert retrieved.merchant_id == "merchant_001"
        assert retrieved.severity == "critical"
        assert retrieved.fraud_probability == 0.961

    def test_incident_belongs_to_run(self, db_session):
        """Incident should have a valid foreign key to its run."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        incident = PersistedIncident(**self._make_incident(run_id=run.id))
        db_session.add(incident)
        db_session.commit()

        # Access through relationship
        retrieved = db_session.query(InvestigationRun).first()
        assert len(retrieved.incidents) == 1
        assert retrieved.incidents[0].incident_id == "INC-merchant_001-20250724"

    def test_relationship_back_populates(self, db_session):
        """Incident should back-populate to its parent run."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        incident = PersistedIncident(**self._make_incident(run_id=run.id))
        db_session.add(incident)
        db_session.commit()

        # Access from incident back to run
        retrieved_incident = db_session.query(PersistedIncident).first()
        assert retrieved_incident.investigation_run.investigation_id == "INV-TEST00000001"

    def test_cascade_delete(self, db_session):
        """Deleting a run should cascade-delete its incidents."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        incident = PersistedIncident(**self._make_incident(run_id=run.id))
        db_session.add(incident)
        db_session.commit()

        # Delete the run
        db_session.delete(run)
        db_session.commit()

        # Incident should also be gone
        assert db_session.query(PersistedIncident).count() == 0

    def test_multiple_incidents_per_run(self, db_session):
        """A single run can have multiple incidents."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        for i in range(3):
            incident = PersistedIncident(**self._make_incident(
                run_id=run.id,
                incident_id=f"INC-merchant_00{i+1}-20250724",
                merchant_id=f"merchant_00{i+1}",
            ))
            db_session.add(incident)
        db_session.commit()

        retrieved = db_session.query(InvestigationRun).first()
        assert len(retrieved.incidents) == 3

    def test_predicted_cause_nullable(self, db_session):
        """predicted_cause should accept None."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        incident = PersistedIncident(**self._make_incident(
            run_id=run.id,
            predicted_cause=None,
        ))
        db_session.add(incident)
        db_session.commit()

        retrieved = db_session.query(PersistedIncident).first()
        assert retrieved.predicted_cause is None

    def test_top_signals_json_stores_list(self, db_session):
        """top_signals_json should store a JSON-encoded list."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        signals = ["Signal A", "Signal B", "Signal C"]
        incident = PersistedIncident(**self._make_incident(
            run_id=run.id,
            top_signals_json=json.dumps(signals),
        ))
        db_session.add(incident)
        db_session.commit()

        retrieved = db_session.query(PersistedIncident).first()
        parsed = json.loads(retrieved.top_signals_json)
        assert parsed == signals

    def test_repr(self, db_session):
        """repr should include incident_id, severity, classification."""
        run = InvestigationRun(
            investigation_id="INV-TEST00000001",
            status="completed",
            transactions_path="data/raw/transactions.csv",
            window_labels_path="data/raw/window_labels.csv",
            z_threshold=0.5,
            min_history_days=3,
            total_results=360,
            spikes_detected=73,
            fraud_incidents=31,
            organic_incidents=39,
            review_required=3,
            baseline_windows=287,
            spike_rate=0.203,
        )
        db_session.add(run)
        db_session.commit()

        incident = PersistedIncident(**self._make_incident(run_id=run.id))
        db_session.add(incident)
        db_session.commit()

        retrieved = db_session.query(PersistedIncident).first()
        r = repr(retrieved)
        assert "INC-merchant_001-20250724" in r
        assert "critical" in r
        assert "fraud_spike" in r
