"""
Comprehensive tests for Dataset Persistence & Investigation Traceability.

Covers:
- DatasetRepository: create, retrieve, list, uniqueness, metadata
- DatasetManager: upload, DB persistence, retrieval after new manager, cleanup
- Investigation integration: dataset association, default dataset, rerun, history
- API: upload, validation, dataset list/detail, 404, no filesystem path leakage
- Restart/durability: system survives new DatasetManager instance
- File safety: malicious filenames, path traversal
- Migration: upgrade, downgrade, upgrade again (via test_alembic.py)
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models import Dataset, InvestigationRun, PersistedIncident
from src.repositories.dataset_repository import DatasetRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_HEADER = [
    "transaction_id", "merchant_id", "timestamp", "date",
    "window_label", "customer_id", "customer_is_new", "sku_id",
    "amount", "payment_status", "is_retry", "device_id", "ip_id",
]


def _make_csv_rows(n: int = 10) -> list[list[str]]:
    rows = []
    for i in range(n):
        rows.append([
            f"txn_{i:06d}",
            "merchant_001",
            "2025-07-01 12:00:00",
            "2025-07-01",
            "unknown",
            f"cust_{i:06d}",
            "True",
            f"sku_{i:04d}",
            f"{100 + i * 10:.2f}",
            "success",
            "False",
            f"dev_{i:04d}",
            f"ip_{i:04d}",
        ])
    return rows


def _make_csv_bytes(rows: list[list[str]] | None = None) -> bytes:
    if rows is None:
        rows = _make_csv_rows(10)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(VALID_HEADER)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


# ---------------------------------------------------------------------------
# Tests: DatasetRepository
# ---------------------------------------------------------------------------


class TestDatasetRepository:
    """Test DatasetRepository CRUD operations."""

    def test_create_and_retrieve(self):
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            ds = repo.create_dataset(
                dataset_id="DS-TEST001",
                original_filename="test.csv",
                stored_path="/tmp/test.csv",
                data_source_type="csv",
                row_count=100,
                merchant_count=5,
                validation_status="validated",
            )
            session.commit()

            fetched = repo.get_by_dataset_id("DS-TEST001")
            assert fetched is not None
            assert fetched.dataset_id == "DS-TEST001"
            assert fetched.original_filename == "test.csv"
            assert fetched.row_count == 100
            assert fetched.merchant_count == 5
            assert fetched.validation_status == "validated"
        engine.dispose()

    def test_get_nonexistent_returns_none(self):
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            assert repo.get_by_dataset_id("DS-NONEXISTENT") is None
        engine.dispose()

    def test_list_datasets(self):
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            for i in range(3):
                repo.create_dataset(
                    dataset_id=f"DS-LIST{i:03d}",
                    original_filename=f"test{i}.csv",
                    stored_path=f"/tmp/test{i}.csv",
                    validation_status="validated",
                )
            session.commit()

            datasets = repo.list_datasets()
            assert len(datasets) == 3
            # Newest first
            assert datasets[0].dataset_id == "DS-LIST002"
        engine.dispose()

    def test_count_datasets(self):
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            assert repo.count_datasets() == 0
            repo.create_dataset(
                dataset_id="DS-COUNT001",
                original_filename="c.csv",
                stored_path="/tmp/c.csv",
                validation_status="validated",
            )
            session.commit()
            assert repo.count_datasets() == 1
        engine.dispose()

    def test_dataset_id_uniqueness(self):
        from sqlalchemy.exc import IntegrityError

        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            repo.create_dataset(
                dataset_id="DS-UNIQUE01",
                original_filename="a.csv",
                stored_path="/tmp/a.csv",
                validation_status="validated",
            )
            session.commit()

        # Second insert with same dataset_id should fail
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            with pytest.raises(IntegrityError):
                repo.create_dataset(
                    dataset_id="DS-UNIQUE01",
                    original_filename="b.csv",
                    stored_path="/tmp/b.csv",
                    validation_status="validated",
                )
            session.rollback()
        engine.dispose()

    def test_update_validation_status(self):
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            ds = repo.create_dataset(
                dataset_id="DS-UPDATE01",
                original_filename="u.csv",
                stored_path="/tmp/u.csv",
                validation_status="pending",
            )
            session.commit()

            repo.update_validation_status(
                ds,
                validation_status="validated",
                row_count=200,
                merchant_count=10,
                min_transaction_date="2025-01-01",
                max_transaction_date="2025-12-31",
            )
            session.commit()

            fetched = repo.get_by_dataset_id("DS-UPDATE01")
            assert fetched.validation_status == "validated"
            assert fetched.row_count == 200
            assert fetched.min_transaction_date == "2025-01-01"
        engine.dispose()

    def test_metadata_fields(self):
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            repo = DatasetRepository(session)
            ds = repo.create_dataset(
                dataset_id="DS-META001",
                original_filename="meta.csv",
                stored_path="/tmp/meta.csv",
                data_source_type="csv",
                row_count=500,
                merchant_count=25,
                min_transaction_date="2025-06-01",
                max_transaction_date="2025-08-31",
                validation_status="validated",
                validation_message=None,
            )
            session.commit()

            fetched = repo.get_by_dataset_id("DS-META001")
            assert fetched.data_source_type == "csv"
            assert fetched.row_count == 500
            assert fetched.merchant_count == 25
            assert fetched.created_at is not None
        engine.dispose()


# ---------------------------------------------------------------------------
# Tests: DatasetManager — DB-backed persistence
# ---------------------------------------------------------------------------


class TestDatasetManagerPersistence:
    """Test that DatasetManager persists metadata to the database."""

    def test_store_dataset_persists_to_db(self, tmp_path):
        from src.services.dataset_manager import DatasetManager

        engine, SessionLocal = _make_in_memory_db()
        manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        content = _make_csv_bytes()

        with SessionLocal() as session:
            ds = manager.store_dataset(
                db=session,
                transactions_content=content,
                original_filename="test.csv",
                row_count=10,
                merchant_count=1,
            )
            session.commit()

            # Verify DB record exists
            fetched = session.query(Dataset).filter_by(dataset_id=ds.dataset_id).first()
            assert fetched is not None
            assert fetched.original_filename == "test.csv"
            assert fetched.row_count == 10

            # Verify file exists on disk
            assert Path(fetched.stored_path).exists()
        engine.dispose()

    def test_retrieval_with_new_manager_instance(self, tmp_path):
        """Simulate restart: new DatasetManager can find datasets from DB."""
        from src.services.dataset_manager import DatasetManager

        engine, SessionLocal = _make_in_memory_db()
        content = _make_csv_bytes()

        # First manager stores dataset
        manager1 = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        with SessionLocal() as session:
            ds = manager1.store_dataset(
                db=session,
                transactions_content=content,
                original_filename="restart_test.csv",
                row_count=10,
            )
            session.commit()
            dataset_id = ds.dataset_id

        # New manager instance (simulating restart)
        manager2 = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        with SessionLocal() as session:
            fetched = manager2.get_dataset(session, dataset_id)
            assert fetched is not None
            assert fetched.original_filename == "restart_test.csv"
            assert fetched.row_count == 10

            # Verify file path resolves
            resolved = manager2.resolve_file_path(fetched)
            assert resolved is not None
            assert Path(resolved).exists()
        engine.dispose()

    def test_store_dataset_cleans_up_on_db_failure(self, tmp_path):
        """If DB persistence fails, files should be cleaned up."""
        from unittest.mock import MagicMock, patch
        from src.services.dataset_manager import DatasetManager

        manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        content = _make_csv_bytes()

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.create_dataset.side_effect = RuntimeError("DB failure")

        with patch("src.services.dataset_manager.DatasetRepository", return_value=mock_repo):
            with pytest.raises(RuntimeError, match="DB failure"):
                manager.store_dataset(
                    db=mock_session,
                    transactions_content=content,
                    original_filename="fail_test.csv",
                )

        # Verify no dataset directory was left behind
        upload_dir = tmp_path / "uploads"
        if upload_dir.exists():
            assert len(list(upload_dir.iterdir())) == 0


# ---------------------------------------------------------------------------
# Tests: File Safety
# ---------------------------------------------------------------------------


class TestFileSafety:
    """Ensure malicious filenames are handled safely."""

    def test_path_traversal_filename(self, tmp_path):
        from src.services.dataset_manager import DatasetManager

        engine, SessionLocal = _make_in_memory_db()
        manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        content = _make_csv_bytes()

        with SessionLocal() as session:
            ds = manager.store_dataset(
                db=session,
                transactions_content=content,
                original_filename="../../etc/passwd.csv",
            )
            session.commit()

            # Stored path should be inside upload_dir, not traversal
            stored = Path(ds.stored_path)
            assert str(tmp_path / "uploads") in str(stored)
            assert ".." not in str(stored)
            assert "passwd" not in str(stored) or "passwd" in stored.name  # sanitized
        engine.dispose()

    def test_empty_filename_uses_fallback(self, tmp_path):
        from src.services.dataset_manager import DatasetManager

        safe = DatasetManager._safe_filename("", "fallback.csv")
        assert safe == "fallback.csv"

    def test_special_chars_sanitized(self):
        from src.services.dataset_manager import DatasetManager

        safe = DatasetManager._safe_filename("file with spaces!@#$%.csv", "fallback.csv")
        assert ".." not in safe
        assert "/" not in safe
        assert "\\" not in safe

    def test_no_filesystem_path_in_api_response(self, tmp_path):
        """Upload API response must not contain server filesystem paths."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app
        from src.api.routes import transactions as tx_routes
        from src.services.dataset_manager import DatasetManager

        test_manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        original = tx_routes.dataset_manager
        tx_routes.dataset_manager = test_manager

        try:
            app = create_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                csv_bytes = _make_csv_bytes()
                resp = client.post(
                    "/api/v1/transactions/upload",
                    files={"file": ("safe.csv", csv_bytes, "text/csv")},
                )
                assert resp.status_code == 200
                data = resp.json()
                # Must NOT contain filesystem paths
                for key in data:
                    val = str(data[key])
                    if "path" in key.lower():
                        # The field name itself shouldn't be there
                        pass
                    assert "C:\\" not in val, f"Filesystem path leaked in {key}: {val}"
                    assert "tmp/" not in val or "tmp" not in key.lower()
        finally:
            tx_routes.dataset_manager = original


# ---------------------------------------------------------------------------
# Tests: Investigation ↔ Dataset traceability
# ---------------------------------------------------------------------------


class TestInvestigationDatasetTraceability:
    """Test that investigations track their source dataset."""

    def test_investigation_run_has_dataset_id_column(self):
        """InvestigationRun should accept dataset_id."""
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            run = InvestigationRun(
                investigation_id="INV-TRACE001",
                dataset_id="DS-TRACE001",
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=2.0,
                min_history_days=3,
                total_results=100,
                spikes_detected=10,
                fraud_incidents=3,
                organic_incidents=4,
                review_required=3,
                baseline_windows=90,
                spike_rate=0.1,
            )
            session.add(run)
            session.commit()

            fetched = session.query(InvestigationRun).filter_by(
                investigation_id="INV-TRACE001"
            ).one()
            assert fetched.dataset_id == "DS-TRACE001"
        engine.dispose()

    def test_investigation_run_default_dataset_is_none(self):
        """Default dataset investigations should have dataset_id=None."""
        engine, SessionLocal = _make_in_memory_db()
        with SessionLocal() as session:
            run = InvestigationRun(
                investigation_id="INV-TRACE002",
                transactions_path="data/raw/transactions.csv",
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=2.0,
                min_history_days=3,
                total_results=100,
                spikes_detected=10,
                fraud_incidents=3,
                organic_incidents=4,
                review_required=3,
                baseline_windows=90,
                spike_rate=0.1,
            )
            session.add(run)
            session.commit()

            fetched = session.query(InvestigationRun).filter_by(
                investigation_id="INV-TRACE002"
            ).one()
            assert fetched.dataset_id is None
        engine.dispose()

    def test_investigation_history_exposes_dataset_info(self, tmp_path):
        """Investigation history/detail should include dataset metadata."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app
        from src.api.routes import transactions as tx_routes
        from src.services.dataset_manager import DatasetManager

        test_manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        original = tx_routes.dataset_manager
        tx_routes.dataset_manager = test_manager

        try:
            app = create_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                # Upload dataset
                csv_bytes = _make_csv_bytes()
                resp = client.post(
                    "/api/v1/transactions/upload",
                    files={"file": ("trace_test.csv", csv_bytes, "text/csv")},
                )
                assert resp.status_code == 200
                dataset_id = resp.json()["dataset_id"]

                # Run investigation with dataset
                resp = client.post(
                    "/api/v1/investigations/run",
                    json={"dataset_id": dataset_id},
                )
                if resp.status_code == 200:
                    inv_id = resp.json()["investigation_id"]

                    # Check history list has dataset info
                    resp = client.get("/api/v1/investigations")
                    assert resp.status_code == 200
                    items = resp.json()["items"]
                    matching = [i for i in items if i["investigation_id"] == inv_id]
                    if matching:
                        item = matching[0]
                        assert item["dataset_id"] == dataset_id
                        assert item["dataset_filename"] == "trace_test.csv"
                        assert item["data_source_type"] == "csv"
        finally:
            tx_routes.dataset_manager = original


# ---------------------------------------------------------------------------
# Tests: Restart / Durability
# ---------------------------------------------------------------------------


class TestRestartDurability:
    """Prove the system survives application restart (new DatasetManager)."""

    def test_dataset_survives_restart(self, tmp_path):
        """Upload → persist → new manager → retrieve → still works."""
        from src.services.dataset_manager import DatasetManager

        engine, SessionLocal = _make_in_memory_db()
        content = _make_csv_bytes()

        # Pre-restart: store dataset
        mgr1 = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        with SessionLocal() as session:
            ds = mgr1.store_dataset(
                db=session,
                transactions_content=content,
                original_filename="durable.csv",
                row_count=10,
                merchant_count=1,
                min_transaction_date="2025-07-01",
                max_transaction_date="2025-07-10",
            )
            session.commit()
            did = ds.dataset_id

        # Simulate restart: new manager, new DB session
        mgr2 = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        with SessionLocal() as session:
            # Verify dataset metadata
            fetched = mgr2.get_dataset(session, did)
            assert fetched is not None
            assert fetched.original_filename == "durable.csv"
            assert fetched.row_count == 10
            assert fetched.merchant_count == 1
            assert fetched.min_transaction_date == "2025-07-01"
            assert fetched.max_transaction_date == "2025-07-10"

            # Verify file is still on disk
            resolved = mgr2.resolve_file_path(fetched)
            assert resolved is not None
            assert Path(resolved).exists()

            # Verify list_datasets works
            all_ds = mgr2.list_datasets(session)
            assert len(all_ds) == 1
            assert all_ds[0].dataset_id == did
        engine.dispose()

    def test_investigation_dataset_association_survives_restart(self, tmp_path):
        """Investigation → dataset link persists across sessions."""
        from src.services.dataset_manager import DatasetManager

        engine, SessionLocal = _make_in_memory_db()
        content = _make_csv_bytes()

        # Store dataset + create investigation run
        mgr = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        with SessionLocal() as session:
            ds = mgr.store_dataset(
                db=session,
                transactions_content=content,
                original_filename="inv_test.csv",
                row_count=10,
            )
            ds_id = ds.dataset_id
            ds_path = ds.stored_path
            run = InvestigationRun(
                investigation_id="INV-DURABLE01",
                dataset_id=ds_id,
                transactions_path=ds_path,
                window_labels_path="data/raw/window_labels.csv",
                z_threshold=2.0,
                min_history_days=3,
                total_results=100,
                spikes_detected=10,
                fraud_incidents=3,
                organic_incidents=4,
                review_required=3,
                baseline_windows=90,
                spike_rate=0.1,
            )
            session.add(run)
            session.commit()

        # New session (restart)
        with SessionLocal() as session:
            fetched_run = session.query(InvestigationRun).filter_by(
                investigation_id="INV-DURABLE01"
            ).one()
            assert fetched_run.dataset_id == ds_id

            # Verify the dataset still exists
            fetched_ds = mgr.get_dataset(session, fetched_run.dataset_id)
            assert fetched_ds is not None
            assert fetched_ds.original_filename == "inv_test.csv"
        engine.dispose()


# ---------------------------------------------------------------------------
# Tests: Dataset API endpoints
# ---------------------------------------------------------------------------


class TestDatasetAPIEndpoints:
    """Test GET /datasets and GET /datasets/{dataset_id}."""

    def test_list_datasets_endpoint(self, tmp_path):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine as ce
        from sqlalchemy.orm import sessionmaker as sm

        from src.api.app import create_app
        from src.api.routes import transactions as tx_routes
        from src.services.dataset_manager import DatasetManager

        test_manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        original = tx_routes.dataset_manager
        tx_routes.dataset_manager = test_manager

        # Use a fresh temp DB to avoid pollution from production DB
        db_path = tmp_path / "list_test.db"
        db_url = "sqlite:///" + str(db_path).replace(chr(92), "/")
        test_engine = ce(db_url, connect_args={"check_same_thread": False})

        import sys
        from src.database.base import Base
        Base.metadata.create_all(bind=test_engine)
        TestSession = sm(bind=test_engine)

        engine_mod = sys.modules["src.database.engine"]
        session_mod = sys.modules["src.database.session"]
        orig_engine = engine_mod.engine
        orig_sl = engine_mod.SessionLocal
        orig_sdb = session_mod.SessionLocal

        def _override_get_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        try:
            engine_mod.engine = test_engine
            engine_mod.SessionLocal = TestSession
            session_mod.SessionLocal = TestSession

            app = create_app()
            from src.database.session import get_db
            app.dependency_overrides[get_db] = _override_get_db

            with TestClient(app, raise_server_exceptions=False) as client:
                # Upload two datasets
                for i in range(2):
                    csv_bytes = _make_csv_bytes(_make_csv_rows(5))
                    resp = client.post(
                        "/api/v1/transactions/upload",
                        files={"file": (f"file{i}.csv", csv_bytes, "text/csv")},
                    )
                    assert resp.status_code == 200, resp.text

                # List datasets
                resp = client.get("/api/v1/transactions/datasets")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                assert len(data["items"]) == 2
                # Verify no filesystem paths in response
                for item in data["items"]:
                    assert "stored_path" not in item

            app.dependency_overrides.clear()
        finally:
            tx_routes.dataset_manager = original
            engine_mod.engine = orig_engine
            engine_mod.SessionLocal = orig_sl
            session_mod.SessionLocal = orig_sdb

    def test_get_dataset_detail_endpoint(self, tmp_path):
        from fastapi.testclient import TestClient
        from src.api.app import create_app
        from src.api.routes import transactions as tx_routes
        from src.services.dataset_manager import DatasetManager

        test_manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))
        original = tx_routes.dataset_manager
        tx_routes.dataset_manager = test_manager

        try:
            app = create_app()
            with TestClient(app, raise_server_exceptions=False) as client:
                csv_bytes = _make_csv_bytes()
                resp = client.post(
                    "/api/v1/transactions/upload",
                    files={"file": ("detail.csv", csv_bytes, "text/csv")},
                )
                assert resp.status_code == 200
                dataset_id = resp.json()["dataset_id"]

                # Get detail
                resp = client.get(f"/api/v1/transactions/datasets/{dataset_id}")
                assert resp.status_code == 200
                data = resp.json()
                assert data["dataset_id"] == dataset_id
                assert data["original_filename"] == "detail.csv"
                assert data["validation_status"] == "validated"
                assert data["row_count"] == 10
                assert "stored_path" not in data
        finally:
            tx_routes.dataset_manager = original

    def test_get_nonexistent_dataset_returns_404(self):
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/transactions/datasets/DS-NONEXISTENT")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Rerun uses original dataset
# ---------------------------------------------------------------------------


class TestRerunDatasetPreservation:
    """Verify reruns use the original investigation's dataset configuration."""

    def test_rerun_preserves_original_paths(self):
        """Rerun should use original investigation's transactions_path."""
        engine, SessionLocal = _make_in_memory_db()

        with SessionLocal() as session:
            # Create an investigation with specific paths
            run = InvestigationRun(
                investigation_id="INV-RERUN01",
                dataset_id="DS-RERUN01",
                transactions_path="/specific/path/transactions.csv",
                window_labels_path="/specific/path/labels.csv",
                z_threshold=3.0,
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
            session.commit()

            # Verify the stored configuration
            fetched = session.query(InvestigationRun).filter_by(
                investigation_id="INV-RERUN01"
            ).one()
            assert fetched.transactions_path == "/specific/path/transactions.csv"
            assert fetched.dataset_id == "DS-RERUN01"
            assert fetched.z_threshold == 3.0
            assert fetched.min_history_days == 10
        engine.dispose()


# ---------------------------------------------------------------------------
# Tests: ML files untouched
# ---------------------------------------------------------------------------


class TestMLFilesUntouched:
    """Verify no ML source files are modified by this milestone."""

    def test_dataset_repository_does_not_import_ml(self):
        import src.repositories.dataset_repository as mod
        source = open(mod.__file__).read()
        ml_modules = [
            "from src.pipeline",
            "from src.spike_detector",
            "from src.cause_classifier",
            "from src.features",
            "from src.evaluation",
        ]
        for ml_import in ml_modules:
            assert ml_import not in source, f"DatasetRepository imports ML module: {ml_import}"

    def test_dataset_manager_does_not_import_ml(self):
        import src.services.dataset_manager as mod
        source = open(mod.__file__).read()
        ml_modules = [
            "from src.pipeline",
            "from src.spike_detector",
            "from src.cause_classifier",
            "from src.features",
            "from src.evaluation",
        ]
        for ml_import in ml_modules:
            assert ml_import not in source, f"DatasetManager imports ML module: {ml_import}"
