"""
Tests for database initialization at application startup.

Verifies that Base.metadata.create_all() correctly creates tables,
is idempotent, preserves existing data, and works with isolated
SQLite databases.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_in_memory_db():
    """Create an isolated in-memory SQLite engine + session factory."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    session_local = sessionmaker(bind=engine)
    return engine, session_local


def _get_table_names(engine) -> set[str]:
    """Return the set of table names in the given engine."""
    inspector = inspect(engine)
    return set(inspector.get_table_names())


# ---------------------------------------------------------------------------
# Table creation tests
# ---------------------------------------------------------------------------

class TestTableCreation:
    """Verify that database tables are created from ORM metadata."""

    def test_create_all_creates_expected_tables(self):
        """create_all on a fresh in-memory DB creates both tables."""
        engine, _ = _make_in_memory_db()

        # Import models to register them with Base.metadata
        import src.database.models  # noqa: F401

        Base.metadata.create_all(bind=engine)

        tables = _get_table_names(engine)
        assert "investigation_runs" in tables
        assert "persisted_incidents" in tables

    def test_create_all_on_empty_metadata_creates_nothing(self):
        """If no models are registered, create_all creates no tables."""
        engine, _ = _make_in_memory_db()
        # Use a fresh metadata to simulate no models
        from sqlalchemy.orm import DeclarativeBase

        class EmptyBase(DeclarativeBase):
            pass

        EmptyBase.metadata.create_all(bind=engine)
        tables = _get_table_names(engine)
        assert len(tables) == 0

    def test_create_all_idempotent(self):
        """Running create_all twice does not raise or create duplicates."""
        engine, _ = _make_in_memory_db()
        import src.database.models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        tables_before = _get_table_names(engine)

        # Run again — should not raise
        Base.metadata.create_all(bind=engine)
        tables_after = _get_table_names(engine)

        assert tables_before == tables_after
        assert len(tables_after) == 3


# ---------------------------------------------------------------------------
# Idempotency — data preservation
# ---------------------------------------------------------------------------

class TestDataPreservation:
    """Verify that re-running create_all does not destroy existing data."""

    def test_existing_records_survive_repeated_create_all(self):
        """Rows inserted before a second create_all are still present."""
        engine, session_factory = _make_in_memory_db()
        import src.database.models  # noqa: F401
        from src.database.models import InvestigationRun

        Base.metadata.create_all(bind=engine)

        # Insert a record
        with session_factory() as session:
            run = InvestigationRun(
                investigation_id="INV-TEST001",
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=2.0,
                min_history_days=3,
                total_results=10,
                spikes_detected=5,
                fraud_incidents=2,
                organic_incidents=2,
                review_required=1,
                baseline_windows=5,
                spike_rate=0.5,
            )
            session.add(run)
            session.commit()

        # Run create_all again
        Base.metadata.create_all(bind=engine)

        # Verify record survived
        with session_factory() as session:
            runs = session.query(InvestigationRun).all()
            assert len(runs) == 1
            assert runs[0].investigation_id == "INV-TEST001"


# ---------------------------------------------------------------------------
# Foreign key relationship
# ---------------------------------------------------------------------------

class TestRelationships:
    """Verify FK relationships work after startup initialization."""

    def test_incident_persists_with_fk_after_create_all(self):
        """PersistedIncident FK to InvestigationRun works after create_all."""
        engine, session_factory = _make_in_memory_db()
        import src.database.models  # noqa: F401
        from src.database.models import InvestigationRun, PersistedIncident

        Base.metadata.create_all(bind=engine)

        with session_factory() as session:
            run = InvestigationRun(
                investigation_id="INV-TEST002",
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=2.5,
                min_history_days=3,
                total_results=20,
                spikes_detected=8,
                fraud_incidents=3,
                organic_incidents=3,
                review_required=2,
                baseline_windows=12,
                spike_rate=0.4,
            )
            session.add(run)
            session.flush()

            incident = PersistedIncident(
                investigation_run_id=run.id,
                incident_id="INC-TEST001",
                merchant_id="merchant_001",
                date="2025-07-24",
                severity="critical",
                status="open",
                classification="fraud_spike",
                fraud_probability=0.961,
                confidence=0.89,
                confidence_band="high_confidence",
                anomaly_score=3.8,
                decision_reason="Test",
                anomaly_summary="Test anomaly",
                top_signals_json="[]",
                recommended_action="Review",
            )
            session.add(incident)
            session.commit()

        # Verify relationship
        with session_factory() as session:
            run = session.query(InvestigationRun).filter_by(
                investigation_id="INV-TEST002"
            ).one()
            assert len(run.incidents) == 1
            assert run.incidents[0].incident_id == "INC-TEST001"
            assert run.incidents[0].merchant_id == "merchant_001"


# ---------------------------------------------------------------------------
# Full application startup simulation
# ---------------------------------------------------------------------------

class TestApplicationStartup:
    """Simulate what _initialize_database() does."""

    def test_simulated_startup_creates_tables(self):
        """Simulating the startup init pattern creates the expected tables."""
        engine, session_factory = _make_in_memory_db()

        # Simulate what _initialize_database does
        from src.database.models import InvestigationRun, PersistedIncident  # noqa: F401

        Base.metadata.create_all(bind=engine)

        tables = _get_table_names(engine)
        assert "investigation_runs" in tables
        assert "persisted_incidents" in tables

    def test_startup_then_persist_investigation(self):
        """Simulate: start app → run investigation → persist → verify."""
        engine, session_factory = _make_in_memory_db()

        # Step 1: Startup init
        import src.database.models  # noqa: F401
        from src.database.models import InvestigationRun, PersistedIncident
        from src.repositories.investigation_repository import (
            InvestigationRepository,
        )

        Base.metadata.create_all(bind=engine)

        # Step 2: Simulate investigation run via repository
        with session_factory() as session:
            repo = InvestigationRepository(session)

            run = repo.create_investigation(
                investigation_id="INV-STARTUP01",
                status="completed",
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=2.0,
                min_history_days=3,
                total_results=360,
                spikes_detected=73,
                fraud_incidents=31,
                organic_incidents=20,
                review_required=3,
                baseline_windows=287,
                spike_rate=0.203,
                processing_note="Test investigation",
            )

            repo.create_incident(
                investigation_run_id=run.id,
                incident_id="INC-STARTUP01",
                merchant_id="merchant_001",
                date="2025-07-24",
                severity="critical",
                status="open",
                classification="fraud_spike",
                fraud_probability=0.961,
                confidence=0.89,
                confidence_band="high_confidence",
                anomaly_score=3.8,
                decision_reason="Coordinated fraud",
                anomaly_summary="Payment failure pattern",
                top_signals_json='[{"signal": "failed_payments", "contribution": 1.824}]',
                recommended_action="Review transactions",
            )

            session.commit()

        # Step 3: Verify persistence
        with session_factory() as session:
            run = session.query(InvestigationRun).filter_by(
                investigation_id="INV-STARTUP01"
            ).one()
            assert run.total_results == 360
            assert run.spikes_detected == 73
            assert len(run.incidents) == 1
            assert run.incidents[0].classification == "fraud_spike"

    def test_startup_is_idempotent_with_data(self):
        """Multiple simulated startups preserve existing data."""
        engine, session_factory = _make_in_memory_db()
        import src.database.models  # noqa: F401
        from src.database.models import InvestigationRun

        # First startup
        Base.metadata.create_all(bind=engine)

        # Insert record
        with session_factory() as session:
            run = InvestigationRun(
                investigation_id="INV-IDEMP01",
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
            )
            session.add(run)
            session.commit()

        # Second startup
        Base.metadata.create_all(bind=engine)

        # Third startup
        Base.metadata.create_all(bind=engine)

        # Data still intact
        with session_factory() as session:
            runs = session.query(InvestigationRun).all()
            assert len(runs) == 1
            assert runs[0].investigation_id == "INV-IDEMP01"


# ---------------------------------------------------------------------------
# Application-level integration test
# ---------------------------------------------------------------------------

class TestAppIntegration:
    """Integration test using the actual FastAPI test client."""

    def test_fresh_db_investigation_persists(self, tmp_path):
        """POST /investigations/run on a fresh temp DB persists the result."""
        import sys
        from unittest.mock import patch

        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine as ce
        from sqlalchemy.orm import sessionmaker

        db_path = tmp_path / "test_sus.db"
        db_url = f"sqlite:///{db_path}"

        test_engine = ce(db_url, connect_args={"check_same_thread": False})
        TestSession = sessionmaker(bind=test_engine)

        # Get module objects from sys.modules to avoid import issues
        engine_module = sys.modules["src.database.engine"]
        session_module = sys.modules["src.database.session"]

        original_engine = engine_module.engine
        original_session_factory = engine_module.SessionLocal
        original_get_db_session = session_module.SessionLocal

        try:
            # Patch engine module
            engine_module.engine = test_engine
            engine_module.SessionLocal = TestSession
            # Patch session module (get_db uses this)
            session_module.SessionLocal = TestSession

            import src.database.models  # noqa: F401
            from src.database.base import Base

            Base.metadata.create_all(bind=test_engine)

            from src.api.app import create_app

            app = create_app()

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/investigations/run",
                    json={
                        "transactions_path": "data/raw/transactions.csv",
                        "window_labels_path": "data/raw/window_labels.csv",
                        "z_threshold": 2.0,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                inv_id = data["investigation_id"]
                assert inv_id.startswith("INV-")

                # Verify the investigation was persisted
                with TestSession() as session:
                    from src.database.models import InvestigationRun

                    run = session.query(InvestigationRun).filter_by(
                        investigation_id=inv_id
                    ).first()
                    assert run is not None
                    assert run.status == "completed"
                    assert len(run.incidents) > 0
        finally:
            engine_module.engine = original_engine
            engine_module.SessionLocal = original_session_factory
            session_module.SessionLocal = original_get_db_session
