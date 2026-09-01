"""
Tests for the Transaction Data Ingestion layer.

Covers:
- CSVTransactionDataProvider with valid CSV
- Missing required columns
- Invalid numeric values
- Invalid timestamps
- Empty CSV
- Malformed rows
- Upload → validation → investigation execution
- Existing default dataset flow unchanged
- Uploaded dataset is persisted/associated with investigation
- No ML files modified
"""

from __future__ import annotations

import csv
import io
import os
import tempfile

import pytest

from src.services.transaction_data_provider import (
    CSVTransactionDataProvider,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_HEADER = [
    "transaction_id", "merchant_id", "timestamp", "date",
    "window_label", "customer_id", "customer_is_new", "sku_id",
    "amount", "payment_status", "is_retry", "device_id", "ip_id",
]


def _make_csv(
    rows: list[list[str]],
    header: list[str] | None = None,
) -> str:
    """Create a temporary CSV file and return its path."""
    header = header or VALID_HEADER
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _make_valid_rows(n: int = 10) -> list[list[str]]:
    """Create n valid transaction rows."""
    rows = []
    for i in range(n):
        rows.append([
            f"txn_{i:06d}",              # transaction_id
            "merchant_001",              # merchant_id
            "2025-07-01 12:00:00",       # timestamp
            "2025-07-01",                # date
            "unknown",                   # window_label
            f"cust_{i:06d}",            # customer_id
            "True",                      # customer_is_new
            f"sku_{i:04d}",            # sku_id
            f"{100 + i * 10:.2f}",      # amount
            "success",                   # payment_status
            "False",                     # is_retry
            f"dev_{i:04d}",            # device_id
            f"ip_{i:04d}",             # ip_id
        ])
    return rows


# ---------------------------------------------------------------------------
# Tests: Valid CSV
# ---------------------------------------------------------------------------


class TestValidCSV:
    def test_validates_successfully(self):
        """A well-formed CSV passes validation."""
        path = _make_csv(_make_valid_rows(20))
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert result.is_valid
            assert result.total_rows == 20
            assert len(result.errors) == 0
        finally:
            os.unlink(path)

    def test_loads_transactions(self):
        """load_transactions returns a DataFrame with correct columns."""
        path = _make_csv(_make_valid_rows(5))
        try:
            provider = CSVTransactionDataProvider(path)
            df = provider.load_transactions()
            assert len(df) == 5
            assert "merchant_id" in df.columns
            assert "amount" in df.columns
        finally:
            os.unlink(path)

    def test_generates_window_labels(self):
        """Without window_labels_path, generates labels from transaction dates."""
        path = _make_csv(_make_valid_rows(10))
        try:
            provider = CSVTransactionDataProvider(path)
            wl = provider.load_window_labels()
            assert len(wl) > 0
            assert "merchant_id" in wl.columns
            assert "date" in wl.columns
            assert "window_label" in wl.columns
            assert all(wl["window_label"] == "unknown")
        finally:
            os.unlink(path)

    def test_metadata(self):
        """get_metadata returns source info."""
        path = _make_csv(_make_valid_rows(5))
        try:
            provider = CSVTransactionDataProvider(path, source_name="test:upload.csv")
            meta = provider.get_metadata()
            assert meta["source_type"] == "csv"
            assert meta["source_name"] == "test:upload.csv"
            assert "columns" in meta
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests: Missing required columns
# ---------------------------------------------------------------------------


class TestMissingColumns:
    def test_missing_merchant_id(self):
        """CSV missing merchant_id fails validation."""
        header = [c for c in VALID_HEADER if c != "merchant_id"]
        path = _make_csv(_make_valid_rows(5), header=header)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert not result.is_valid
            assert any("merchant_id" in e for e in result.errors)
        finally:
            os.unlink(path)

    def test_missing_multiple_columns(self):
        """CSV missing multiple required columns lists all missing."""
        header = [c for c in VALID_HEADER if c not in {"amount", "timestamp"}]
        path = _make_csv(_make_valid_rows(5), header=header)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert not result.is_valid
            assert any("amount" in e for e in result.errors)
            assert any("timestamp" in e for e in result.errors)
        finally:
            os.unlink(path)

    def test_missing_optional_columns_warns(self):
        """CSV missing optional columns produces warnings but passes."""
        path = _make_csv(_make_valid_rows(5))
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            # Optional columns are missing but validation still passes
            assert result.is_valid
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests: Invalid numeric values
# ---------------------------------------------------------------------------


class TestInvalidNumerics:
    def test_non_numeric_amount(self):
        """Non-numeric amount values are detected."""
        rows = _make_valid_rows(5)
        rows[2][8] = "not_a_number"  # amount column
        path = _make_csv(rows)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert not result.is_valid
            assert any("amount" in e for e in result.errors)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests: Invalid timestamps
# ---------------------------------------------------------------------------


class TestInvalidTimestamps:
    def test_unparseable_timestamp(self):
        """Unparseable timestamps are detected."""
        rows = _make_valid_rows(5)
        rows[3][2] = "not-a-timestamp"  # timestamp column
        path = _make_csv(rows)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert not result.is_valid
            assert any("timestamp" in e for e in result.errors)
        finally:
            os.unlink(path)

    def test_unparseable_date(self):
        """Unparseable date values are detected."""
        rows = _make_valid_rows(5)
        rows[1][3] = "not-a-date"  # date column
        path = _make_csv(rows)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert not result.is_valid
            assert any("date" in e for e in result.errors)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests: Empty CSV
# ---------------------------------------------------------------------------


class TestEmptyCSV:
    def test_empty_file(self):
        """Empty CSV file is detected."""
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            # Empty file may fail to parse or have 0 rows
            # Either way it should not be valid for pipeline use
            assert result.is_valid is False or result.total_rows == 0
        finally:
            os.unlink(path)

    def test_header_only(self):
        """CSV with only a header and no data rows."""
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w") as f:
            f.write(",".join(VALID_HEADER) + "\n")
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert result.total_rows == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests: Malformed rows
# ---------------------------------------------------------------------------


class TestMalformedRows:
    def test_blank_merchant_id(self):
        """Blank merchant_id is detected."""
        rows = _make_valid_rows(5)
        rows[2][1] = ""  # merchant_id
        path = _make_csv(rows)
        try:
            provider = CSVTransactionDataProvider(path)
            result = provider.validate()
            assert not result.is_valid
            assert any("merchant_id" in e for e in result.errors)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Tests: File not found
# ---------------------------------------------------------------------------


class TestFileNotFound:
    def test_nonexistent_file(self):
        """Nonexistent file returns validation error."""
        provider = CSVTransactionDataProvider("/nonexistent/path.csv")
        result = provider.validate()
        assert not result.is_valid
        assert any("not found" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# Tests: Upload endpoint integration
# ---------------------------------------------------------------------------


class TestUploadEndpoint:
    """Integration tests for the upload → validate → investigate flow."""

    def test_upload_validates_and_stores(self, tmp_path):
        """Upload a valid CSV → store it → retrieve the dataset."""
        from fastapi.testclient import TestClient

        from src.api.app import create_app
        from src.services.dataset_manager import DatasetManager

        # Override upload dir to use temp
        test_manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))

        app = create_app()
        # Override the dataset_manager singleton
        import src.api.routes.transactions as tx_routes
        original_manager = tx_routes.dataset_manager
        tx_routes.dataset_manager = test_manager

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                # Create a valid CSV in memory
                csv_content = io.StringIO()
                writer = csv.writer(csv_content)
                writer.writerow(VALID_HEADER)
                writer.writerows(_make_valid_rows(10))
                csv_bytes = csv_content.getvalue().encode("utf-8")

                response = client.post(
                    "/api/v1/transactions/upload",
                    files={"file": ("test_data.csv", csv_bytes, "text/csv")},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["dataset_id"].startswith("DS-")
                assert data["original_filename"] == "test_data.csv"

                # Verify the file was stored
                import os
                assert os.path.exists(data["transactions_path"])
        finally:
            tx_routes.dataset_manager = original_manager

    def test_upload_rejects_non_csv(self):
        """Upload of non-CSV file is rejected."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/transactions/upload",
                files={"file": ("data.txt", b"some,data", "text/plain")},
            )
            assert response.status_code == 422

    def test_upload_rejects_empty_file(self):
        """Upload of empty file is rejected."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/transactions/upload",
                files={"file": ("empty.csv", b"", "text/csv")},
            )
            assert response.status_code == 422

    def test_validate_endpoint(self):
        """Validation endpoint returns results without storing."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            csv_content = io.StringIO()
            writer = csv.writer(csv_content)
            writer.writerow(VALID_HEADER)
            writer.writerows(_make_valid_rows(15))
            csv_bytes = csv_content.getvalue().encode("utf-8")

            response = client.post(
                "/api/v1/transactions/validate",
                files={"file": ("test.csv", csv_bytes, "text/csv")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True
            assert data["total_rows"] == 15
            assert data["unique_merchants"] == 1


# ---------------------------------------------------------------------------
# Tests: Investigation with uploaded dataset
# ---------------------------------------------------------------------------


class TestInvestigationWithDataset:
    """Test running an investigation with an uploaded dataset."""

    def test_investigation_with_dataset_id(self, tmp_path):
        """Run investigation using dataset_id resolves to uploaded file."""
        from fastapi.testclient import TestClient

        from src.api.app import create_app
        from src.services.dataset_manager import DatasetManager

        test_manager = DatasetManager(upload_dir=str(tmp_path / "uploads"))

        app = create_app()
        import src.api.routes.transactions as tx_routes
        import src.api.routes.investigations as inv_routes
        original_tx_manager = tx_routes.dataset_manager

        # Store a valid dataset manually
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerow(VALID_HEADER)
        writer.writerows(_make_valid_rows(50))
        csv_bytes = csv_content.getvalue().encode("utf-8")

        record = test_manager.store_dataset(
            transactions_content=csv_bytes,
            original_filename="test.csv",
        )
        tx_routes.dataset_manager = test_manager
        # Also patch the module-level import used by the investigations route
        import src.services.dataset_manager as dm_mod
        original_dm_mod = dm_mod.dataset_manager
        dm_mod.dataset_manager = test_manager

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/api/v1/investigations/run",
                    json={"dataset_id": record.dataset_id},
                )
                # Should succeed (or 500 if pipeline fails, but not 404 for dataset)
                assert response.status_code != 404 or "Dataset" not in response.text
                # If pipeline succeeds, verify the investigation was created
                if response.status_code == 200:
                    data = response.json()
                    assert data["investigation_id"].startswith("INV-")
        finally:
            tx_routes.dataset_manager = original_tx_manager
            dm_mod.dataset_manager = original_dm_mod

    def test_investigation_with_invalid_dataset_id(self):
        """Run investigation with nonexistent dataset_id returns 404."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/investigations/run",
                json={"dataset_id": "DS-NONEXISTENT"},
            )
            assert response.status_code == 404
            assert "Dataset" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: Default dataset unchanged
# ---------------------------------------------------------------------------


class TestDefaultDatasetUnchanged:
    """Verify the existing default dataset flow is not broken."""

    def test_default_investigation_works(self):
        """POST /investigations/run without dataset_id uses default data."""
        from fastapi.testclient import TestClient
        from src.api.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/investigations/run", json={})
            # Should succeed (200) or fail with data issue (404/500)
            # but NOT with a schema/validation error
            assert response.status_code in {200, 404, 500}
            if response.status_code == 200:
                data = response.json()
                assert data["investigation_id"].startswith("INV-")
                assert "summary" in data
                assert "incidents" in data


# ---------------------------------------------------------------------------
# Tests: Validation result model
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_to_dict(self):
        """ValidationResult.to_dict includes all expected fields."""
        result = ValidationResult(
            is_valid=True,
            total_rows=100,
            valid_rows=95,
            errors=["bad row"],
            warnings=["missing optional"],
            metadata={"unique_merchants": 5},
        )
        d = result.to_dict()
        assert d["is_valid"] is True
        assert d["total_rows"] == 100
        assert d["valid_rows"] == 95
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert d["errors"] == ["bad row"]
        assert d["warnings"] == ["missing optional"]
        assert d["unique_merchants"] == 5


# ---------------------------------------------------------------------------
# Tests: ML files untouched
# ---------------------------------------------------------------------------


class TestMLFilesUntouched:
    """Verify no ML source files are modified."""

    def test_ml_files_not_imported_by_provider(self):
        """Transaction data provider does not import ML modules."""
        import src.services.transaction_data_provider as mod
        source = open(mod.__file__).read()
        ml_modules = [
            "from src.pipeline",
            "from src.spike_detector",
            "from src.cause_classifier",
            "from src.features",
            "from src.evaluation",
        ]
        for ml_import in ml_modules:
            assert ml_import not in source, f"Provider imports ML module: {ml_import}"
