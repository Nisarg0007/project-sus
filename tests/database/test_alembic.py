"""
Tests for Alembic database migration infrastructure.

Covers:
- Alembic configuration uses current database URL
- Fresh upgrade creates all expected schema
- Upgrade is idempotent
- Downgrade removes schema
- Upgrade after downgrade recreates schema
- Existing persisted data survives upgrade (idempotent no-op)
- Expected indexes and constraints exist
- All ORM tables are represented by migration metadata
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.database.base import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_url(db_path: str) -> str:
    """Convert a file path to a SQLAlchemy sqlite URL, handling Windows backslashes."""
    return "sqlite:///" + db_path.replace(chr(92), "/")


def _alembic_cfg(db_url: str | None = None):
    """Create an Alembic Config pointing at a specific database URL."""
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _run_upgrade(db_url: str):
    """Run alembic upgrade head against the given database URL."""
    import os
    from alembic import command as alembic_command

    # env.py reads SUS_DATABASE_URL to override the default settings URL
    old_env = os.environ.get("SUS_DATABASE_URL")
    os.environ["SUS_DATABASE_URL"] = db_url
    try:
        cfg = _alembic_cfg(db_url)
        alembic_command.upgrade(cfg, "head")
    finally:
        if old_env is None:
            os.environ.pop("SUS_DATABASE_URL", None)
        else:
            os.environ["SUS_DATABASE_URL"] = old_env


def _run_downgrade(db_url: str):
    """Run alembic downgrade base against the given database URL."""
    import os
    from alembic import command as alembic_command

    old_env = os.environ.get("SUS_DATABASE_URL")
    os.environ["SUS_DATABASE_URL"] = db_url
    try:
        cfg = _alembic_cfg(db_url)
        alembic_command.downgrade(cfg, "base")
    finally:
        if old_env is None:
            os.environ.pop("SUS_DATABASE_URL", None)
        else:
            os.environ["SUS_DATABASE_URL"] = old_env


def _get_tables(db_path: str) -> set[str]:
    """Return the set of user table names (excluding alembic_version)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    return tables


def _get_indexes(db_path: str, table: str) -> dict[str, list[str]]:
    """Return indexes and their columns for a table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Use PRAGMA index_list to get indexes, then PRAGMA index_info for columns
    cursor.execute(f"PRAGMA index_list({table})")
    indexes = {}
    for row in cursor.fetchall():
        idx_name = row[1]
        if idx_name.startswith("sqlite_autoindex"):
            continue
        cursor.execute(f"PRAGMA index_info({idx_name})")
        cols = [info[2].lower() for info in cursor.fetchall()]
        indexes[idx_name] = cols
    conn.close()
    return indexes


def _get_alembic_version(db_path: str) -> str | None:
    """Return the current alembic version stamp, or None."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version_num FROM alembic_version")
        row = cursor.fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fresh_db(tmp_path):
    """Provide a path to a fresh (non-existent) SQLite database file."""
    db_path = str(tmp_path / "test_alembic.db")
    yield db_path
    # Cleanup is handled by tmp_path


@pytest.fixture()
def fresh_db_url(fresh_db):
    """Provide a SQLAlchemy URL for the fresh database."""
    # On Windows, tmp_path produces backslashes; SQLAlchemy needs forward slashes
    return _db_url(fresh_db)


@pytest.fixture()
def migrated_db(fresh_db):
    """Provide a database that has been upgraded to head."""
    db_url = _db_url(fresh_db)
    _run_upgrade(db_url)
    return fresh_db


# ---------------------------------------------------------------------------
# Tests: Configuration
# ---------------------------------------------------------------------------


class TestAlembicConfiguration:
    """Verify Alembic is correctly configured."""

    def test_alembic_ini_exists(self):
        """alembic.ini exists in project root."""
        ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
        assert ini_path.exists(), f"Missing {ini_path}"

    def test_alembic_env_exists(self):
        """alembic/env.py exists."""
        env_path = Path(__file__).resolve().parents[1].parent / "alembic" / "env.py"
        assert env_path.exists(), f"Missing {env_path}"

    def test_initial_migration_exists(self):
        """At least one migration file exists in versions/."""
        versions_dir = Path(__file__).resolve().parents[1].parent / "alembic" / "versions"
        migration_files = list(versions_dir.glob("*.py"))
        # Exclude __init__.py and __pycache__
        migration_files = [f for f in migration_files if f.name != "__init__.py"]
        assert len(migration_files) >= 1, "No migration files found"

    def test_database_url_comes_from_settings(self):
        """Alembic uses the application's database URL from Settings."""
        cfg = _alembic_cfg()
        url = cfg.get_main_option("sqlalchemy.url")
        # env.py overrides this at runtime from settings, but the config
        # should at least have a sensible default
        assert url is not None
        assert "sqlite" in url.lower() or "postgresql" in url.lower()


# ---------------------------------------------------------------------------
# Tests: Fresh upgrade
# ---------------------------------------------------------------------------


class TestFreshUpgrade:
    """Verify that upgrading a fresh database creates all expected schema."""

    def test_creates_all_tables(self, migrated_db):
        """Fresh upgrade creates all expected tables."""
        tables = _get_tables(migrated_db)
        assert "investigation_runs" in tables
        assert "persisted_incidents" in tables
        assert "incident_status_history" in tables
        assert "datasets" in tables
        assert len(tables) == 4

    def test_creates_alembic_version(self, migrated_db):
        """Upgrade stamps the alembic_version table."""
        version = _get_alembic_version(migrated_db)
        assert version is not None

    def test_investigation_runs_columns(self, migrated_db):
        """investigation_runs has all expected columns."""
        conn = sqlite3.connect(migrated_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(investigation_runs)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "id", "investigation_id", "status", "created_at",
            "dataset_id",
            "transactions_path", "window_labels_path", "model_path",
            "z_threshold", "min_history_days", "merchant_filter",
            "total_results", "spikes_detected", "fraud_incidents",
            "organic_incidents", "review_required", "baseline_windows",
            "spike_rate", "processing_note",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_persisted_incidents_columns(self, migrated_db):
        """persisted_incidents has all expected columns."""
        conn = sqlite3.connect(migrated_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(persisted_incidents)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "id", "investigation_run_id", "incident_id", "merchant_id", "date",
            "severity", "status", "classification", "predicted_cause",
            "fraud_probability", "confidence", "confidence_band", "anomaly_score",
            "decision_reason", "anomaly_summary", "top_signals_json", "recommended_action",
            "workflow_status", "assigned_analyst", "analyst_notes", "resolution",
            "created_at", "updated_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_incident_status_history_columns(self, migrated_db):
        """incident_status_history has all expected columns."""
        conn = sqlite3.connect(migrated_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(incident_status_history)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "id", "incident_id", "old_status", "new_status",
            "changed_by", "note", "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_datasets_columns(self, migrated_db):
        """datasets table has all expected columns."""
        conn = sqlite3.connect(migrated_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(datasets)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "id", "dataset_id", "original_filename", "stored_path",
            "data_source_type", "row_count", "merchant_count",
            "min_transaction_date", "max_transaction_date",
            "validation_status", "validation_message", "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"


# ---------------------------------------------------------------------------
# Tests: Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Verify that upgrade is idempotent."""

    def test_upgrade_twice_succeeds(self, fresh_db_url, fresh_db):
        """Running upgrade head twice does not error."""
        _run_upgrade(fresh_db_url)
        # Should not raise
        _run_upgrade(fresh_db_url)
        tables = _get_tables(fresh_db)
        assert len(tables) == 4

    def test_upgrade_preserves_data(self, fresh_db):
        """Running upgrade on an already-migrated DB is a no-op."""
        db_url = _db_url(fresh_db)
        _run_upgrade(db_url)

        # Insert data
        conn = sqlite3.connect(fresh_db)
        conn.execute("""
            INSERT INTO investigation_runs
            (investigation_id, status, created_at, transactions_path,
             window_labels_path, z_threshold, min_history_days,
             total_results, spikes_detected, fraud_incidents,
             organic_incidents, review_required, baseline_windows,
             spike_rate, processing_note)
            VALUES ('INV-PERSIST-001', 'completed', datetime('now'), 'a.csv', 'b.csv',
                    2.0, 30, 100, 10, 3, 4, 3, 90, 0.1, 'Test')
        """)
        conn.commit()
        conn.close()

        # Run upgrade again — should be no-op
        _run_upgrade(db_url)

        # Data should survive
        conn = sqlite3.connect(fresh_db)
        cursor = conn.cursor()
        cursor.execute("SELECT investigation_id FROM investigation_runs")
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "INV-PERSIST-001"


# ---------------------------------------------------------------------------
# Tests: Downgrade
# ---------------------------------------------------------------------------


class TestDowngrade:
    """Verify that downgrade removes the schema."""

    def test_downgrade_removes_all_tables(self, fresh_db):
        """Downgrade drops all application tables."""
        db_url = _db_url(fresh_db)
        _run_upgrade(db_url)

        # Verify tables exist
        tables_before = _get_tables(fresh_db)
        assert len(tables_before) == 4

        # Downgrade
        _run_downgrade(db_url)

        # Verify tables are gone
        tables_after = _get_tables(fresh_db)
        assert len(tables_after) == 0

    def test_downgrade_removes_alembic_version(self, fresh_db):
        """Downgrade also removes the alembic_version table contents."""
        db_url = _db_url(fresh_db)
        _run_upgrade(db_url)
        _run_downgrade(db_url)

        version = _get_alembic_version(fresh_db)
        assert version is None

    def test_upgrade_after_downgrade_works(self, fresh_db):
        """Upgrade → downgrade → upgrade recreates the schema."""
        db_url = _db_url(fresh_db)
        _run_upgrade(db_url)
        _run_downgrade(db_url)

        # Re-upgrade
        _run_upgrade(db_url)

        tables = _get_tables(fresh_db)
        assert "investigation_runs" in tables
        assert "persisted_incidents" in tables
        assert "incident_status_history" in tables
        assert "datasets" in tables
        assert len(tables) == 4

        version = _get_alembic_version(fresh_db)
        assert version is not None


# ---------------------------------------------------------------------------
# Tests: Indexes and constraints
# ---------------------------------------------------------------------------


class TestIndexesAndConstraints:
    """Verify expected indexes and constraints exist after migration."""

    def test_investigation_id_unique_index(self, migrated_db):
        """investigation_runs has a unique index on investigation_id."""
        indexes = _get_indexes(migrated_db, "investigation_runs")
        # SQLite may name it differently; check that an index exists on investigation_id
        found = any(
            "investigation_id" in cols
            for cols in indexes.values()
        )
        assert found, f"No index on investigation_id found: {indexes}"

    def test_persisted_incidents_indexes(self, migrated_db):
        """persisted_incidents has indexes on key query columns."""
        indexes = _get_indexes(migrated_db, "persisted_incidents")
        all_cols = set()
        for cols in indexes.values():
            all_cols.update(cols)

        # Individual column indexes
        assert "investigation_run_id" in all_cols
        assert "incident_id" in all_cols
        assert "merchant_id" in all_cols
        assert "severity" in all_cols
        assert "classification" in all_cols
        assert "workflow_status" in all_cols

        # Composite indexes
        assert "ix_incidents_merchant_date" in indexes or any(
            cols == ["merchant_id", "date"] for cols in indexes.values()
        ), f"Missing merchant_date composite index: {indexes}"

        assert "ix_incidents_classification_severity" in indexes or any(
            cols == ["classification", "severity"] for cols in indexes.values()
        ), f"Missing classification_severity composite index: {indexes}"

    def test_status_history_index(self, migrated_db):
        """incident_status_history has an index on incident_id."""
        indexes = _get_indexes(migrated_db, "incident_status_history")
        found = any(
            "incident_id" in cols
            for cols in indexes.values()
        )
        assert found, f"No index on incident_id found: {indexes}"


# ---------------------------------------------------------------------------
# Tests: ORM metadata coverage
# ---------------------------------------------------------------------------


class TestORMCoverage:
    """Verify that all ORM tables are represented by migration metadata."""

    def test_all_orm_tables_have_migration(self, migrated_db):
        """Every table in Base.metadata exists in the migrated database."""
        # Import models to populate Base.metadata
        import src.database.models  # noqa: F401

        orm_tables = set(Base.metadata.tables.keys())
        db_tables = _get_tables(migrated_db)

        # ORM tables should be a subset of DB tables
        # (DB might have alembic_version, which is not in ORM)
        missing = orm_tables - db_tables
        assert not missing, f"ORM tables not in database after migration: {missing}"

    def test_migration_tables_match_orm(self, migrated_db):
        """All non-alembic DB tables are represented in ORM metadata."""
        import src.database.models  # noqa: F401

        orm_tables = set(Base.metadata.tables.keys())
        db_tables = _get_tables(migrated_db)

        # DB tables should match ORM tables (minus alembic_version which we excluded)
        extra = db_tables - orm_tables
        assert not extra, f"DB tables not in ORM metadata: {extra}"


# ---------------------------------------------------------------------------
# Tests: Data operations after migration
# ---------------------------------------------------------------------------


class TestDataOperationsAfterMigration:
    """Verify that ORM operations work correctly after Alembic migration."""

    def test_insert_and_retrieve_investigation(self, migrated_db):
        """Can insert and retrieve an InvestigationRun via ORM after migration."""
        db_url = _db_url(migrated_db)
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(bind=engine)

        import src.database.models  # noqa: F401
        from src.database.models import InvestigationRun

        with SessionLocal() as session:
            run = InvestigationRun(
                investigation_id="INV-ORM-001",
                status="completed",
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=3.0,
                min_history_days=30,
                total_results=100,
                spikes_detected=10,
                fraud_incidents=3,
                organic_incidents=4,
                review_required=3,
                baseline_windows=90,
                spike_rate=0.10,
                processing_note="Test",
            )
            session.add(run)
            session.commit()
            assert run.id is not None

        with SessionLocal() as session:
            fetched = session.query(InvestigationRun).filter_by(
                investigation_id="INV-ORM-001"
            ).one()
            assert fetched.status == "completed"
            assert fetched.total_results == 100

        engine.dispose()

    def test_insert_with_relationships(self, migrated_db):
        """Can insert incident with FK relationship after migration."""
        db_url = _db_url(migrated_db)
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(bind=engine)

        import src.database.models  # noqa: F401
        from src.database.models import (
            InvestigationRun,
            PersistedIncident,
            IncidentStatusHistory,
        )

        with SessionLocal() as session:
            run = InvestigationRun(
                investigation_id="INV-RELS-001",
                transactions_path="a.csv",
                window_labels_path="b.csv",
                z_threshold=2.0,
                min_history_days=10,
                total_results=50,
                spikes_detected=5,
                fraud_incidents=2,
                organic_incidents=2,
                review_required=1,
                baseline_windows=40,
                spike_rate=0.1,
            )
            session.add(run)
            session.flush()

            inc = PersistedIncident(
                investigation_run_id=run.id,
                incident_id="INC-RELS-001",
                merchant_id="merch_001",
                date="2025-07-24",
                severity="high",
                classification="fraud_spike",
                fraud_probability=0.85,
                confidence=0.72,
                confidence_band="high_confidence",
                anomaly_score=3.5,
            )
            session.add(inc)
            session.flush()

            hist = IncidentStatusHistory(
                incident_id=inc.id,
                old_status="open",
                new_status="investigating",
                changed_by="analyst_A",
            )
            session.add(hist)
            session.commit()

        with SessionLocal() as session:
            fetched_inc = session.query(PersistedIncident).filter_by(
                incident_id="INC-RELS-001"
            ).one()
            assert fetched_inc.investigation_run.investigation_id == "INV-RELS-001"
            assert len(fetched_inc.status_history) == 1
            assert fetched_inc.status_history[0].new_status == "investigating"

        engine.dispose()

    def test_cascade_delete(self, migrated_db):
        """Deleting an investigation_run cascades to incidents and history."""
        db_url = _db_url(migrated_db)
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(bind=engine)

        import src.database.models  # noqa: F401
        from src.database.models import (
            InvestigationRun,
            PersistedIncident,
            IncidentStatusHistory,
        )

        with SessionLocal() as session:
            run = InvestigationRun(
                investigation_id="INV-CASCADE-001",
                transactions_path="a.csv",
                window_labels_path="b.csv",
                z_threshold=2.0,
                min_history_days=10,
                total_results=50,
                spikes_detected=5,
                fraud_incidents=2,
                organic_incidents=2,
                review_required=1,
                baseline_windows=40,
                spike_rate=0.1,
            )
            session.add(run)
            session.flush()

            inc = PersistedIncident(
                investigation_run_id=run.id,
                incident_id="INC-CASCADE-001",
                merchant_id="merch_001",
                date="2025-07-24",
                severity="high",
                classification="fraud_spike",
                fraud_probability=0.85,
                confidence=0.72,
                confidence_band="high_confidence",
                anomaly_score=3.5,
            )
            session.add(inc)
            session.flush()

            hist = IncidentStatusHistory(
                incident_id=inc.id,
                old_status="open",
                new_status="investigating",
            )
            session.add(hist)
            session.commit()

            # Delete the investigation run
            session.delete(run)
            session.commit()

        with SessionLocal() as session:
            assert session.query(InvestigationRun).count() == 0
            assert session.query(PersistedIncident).count() == 0
            assert session.query(IncidentStatusHistory).count() == 0

        engine.dispose()
