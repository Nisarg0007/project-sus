"""
Dataset Manager for SUS — Spike Understanding System.

Manages uploaded transaction datasets: storage, retrieval, and metadata.
Files are stored outside source code in a configurable upload directory.

Design:
- Each upload gets a unique dataset ID and directory.
- Files are stored with sanitized filenames under the dataset directory.
- Metadata is persisted to the database via DatasetRepository.
- The manager coordinates file I/O and database writes with cleanup on failure.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.config import settings
from src.database.models import Dataset
from src.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages uploaded transaction datasets.

    Stores files in the configured upload directory with unique dataset IDs.
    Database is the source of truth for metadata — no in-memory registry.
    """

    def __init__(self, upload_dir: Optional[str] = None):
        self.upload_dir = Path(upload_dir or settings.upload_dir)

    def _ensure_upload_dir(self) -> None:
        """Create the upload directory if it doesn't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def store_dataset(
        self,
        db: Session,
        transactions_content: bytes,
        original_filename: str,
        window_labels_content: Optional[bytes] = None,
        window_labels_filename: Optional[str] = None,
        *,
        row_count: Optional[int] = None,
        merchant_count: Optional[int] = None,
        min_transaction_date: Optional[str] = None,
        max_transaction_date: Optional[str] = None,
    ) -> Dataset:
        """Store an uploaded dataset and persist metadata to the database.

        Failure ordering:
        1. Generate dataset ID
        2. Write files to disk
        3. Persist metadata to database
        If database persistence fails, clean up the files.
        If file write fails, no database record is created.

        Args:
            db: Active database session.
            transactions_content: Raw bytes of the transactions CSV.
            original_filename: Original filename for reference.
            window_labels_content: Optional raw bytes of window labels CSV.
            window_labels_filename: Optional original filename for window labels.
            row_count: Number of transaction rows (from validation).
            merchant_count: Number of unique merchants.
            min_transaction_date: Earliest transaction date.
            max_transaction_date: Latest transaction date.

        Returns:
            Dataset ORM object with all metadata.
        """
        self._ensure_upload_dir()

        dataset_id = f"DS-{uuid.uuid4().hex[:12].upper()}"
        dataset_dir = self.upload_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Store transactions CSV
            safe_filename = self._safe_filename(original_filename, "transactions.csv")
            transactions_path = dataset_dir / safe_filename
            transactions_path.write_bytes(transactions_content)
            logger.info(
                "Stored transactions: %s (%d bytes)", transactions_path, len(transactions_content)
            )

            # Store window labels if provided
            window_labels_path = None
            if window_labels_content is not None:
                wl_filename = self._safe_filename(
                    window_labels_filename or "window_labels.csv", "window_labels.csv"
                )
                wl_path = dataset_dir / wl_filename
                wl_path.write_bytes(window_labels_content)
                window_labels_path = str(wl_path)
                logger.info("Stored window labels: %s (%d bytes)", wl_path, len(window_labels_content))

            # Persist metadata to database
            repo = DatasetRepository(db)
            ds = repo.create_dataset(
                dataset_id=dataset_id,
                original_filename=original_filename,
                stored_path=str(transactions_path),
                data_source_type="csv",
                row_count=row_count,
                merchant_count=merchant_count,
                min_transaction_date=min_transaction_date,
                max_transaction_date=max_transaction_date,
                validation_status="validated",
            )

            logger.info("Dataset registered: %s (%s)", dataset_id, original_filename)
            return ds

        except Exception:
            # Clean up files on database failure
            if dataset_dir.exists():
                shutil.rmtree(dataset_dir, ignore_errors=True)
                logger.warning("Cleaned up dataset directory after failure: %s", dataset_dir)
            raise

    def get_dataset(self, db: Session, dataset_id: str) -> Optional[Dataset]:
        """Retrieve a dataset record by ID from the database."""
        repo = DatasetRepository(db)
        return repo.get_by_dataset_id(dataset_id)

    def list_datasets(self, db: Session, *, limit: int = 100, offset: int = 0) -> list[Dataset]:
        """List all stored datasets from the database."""
        repo = DatasetRepository(db)
        return repo.list_datasets(limit=limit, offset=offset)

    def resolve_file_path(self, dataset: Dataset) -> Optional[str]:
        """Resolve the stored file path from a dataset record.

        Returns the path as a string if the file exists on disk, None otherwise.
        Does NOT expose the path if the file has been deleted.
        """
        path = Path(dataset.stored_path)
        if path.exists():
            return str(path)
        return None

    @staticmethod
    def _safe_filename(original: str, fallback: str) -> str:
        """Sanitize a filename for safe storage.

        Prevents path traversal by:
        - Stripping directory components (keeps only basename)
        - Replacing non-alphanumeric characters (except ._-)
        - Falling back to a safe default if the result is empty
        """
        # Remove path components, keep only the basename
        name = Path(original).name
        # Replace problematic characters
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        return safe if safe else fallback
