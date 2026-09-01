"""
Dataset Manager for SUS — Spike Understanding System.

Manages uploaded transaction datasets: storage, retrieval, and metadata.
Files are stored outside source code in a configurable upload directory.

Design:
- Each upload gets a unique dataset ID and directory.
- Files are stored with original filenames under the dataset directory.
- Metadata is tracked in-memory (sufficient for single-process deployment).
- Future: persist metadata to database.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)


class DatasetRecord:
    """Metadata for a stored dataset."""

    def __init__(
        self,
        dataset_id: str,
        transactions_path: str,
        window_labels_path: Optional[str],
        original_filename: str,
        source_name: str,
        created_at: str,
    ):
        self.dataset_id = dataset_id
        self.transactions_path = transactions_path
        self.window_labels_path = window_labels_path
        self.original_filename = original_filename
        self.source_name = source_name
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "transactions_path": self.transactions_path,
            "window_labels_path": self.window_labels_path,
            "original_filename": self.original_filename,
            "source_name": self.source_name,
            "created_at": self.created_at,
        }


class DatasetManager:
    """Manages uploaded transaction datasets.

    Stores files in the configured upload directory with unique dataset IDs.
    """

    def __init__(self, upload_dir: Optional[str] = None):
        self.upload_dir = Path(upload_dir or settings.upload_dir)
        self._records: dict[str, DatasetRecord] = {}

    def _ensure_upload_dir(self) -> None:
        """Create the upload directory if it doesn't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def store_dataset(
        self,
        transactions_content: bytes,
        original_filename: str,
        window_labels_content: Optional[bytes] = None,
        window_labels_filename: Optional[str] = None,
    ) -> DatasetRecord:
        """Store an uploaded dataset and return its record.

        Args:
            transactions_content: Raw bytes of the transactions CSV.
            original_filename: Original filename for reference.
            window_labels_content: Optional raw bytes of window labels CSV.
            window_labels_filename: Optional original filename for window labels.

        Returns:
            DatasetRecord with paths and metadata.
        """
        self._ensure_upload_dir()

        dataset_id = f"DS-{uuid.uuid4().hex[:12].upper()}"
        dataset_dir = self.upload_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

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

        record = DatasetRecord(
            dataset_id=dataset_id,
            transactions_path=str(transactions_path),
            window_labels_path=window_labels_path,
            original_filename=original_filename,
            source_name=f"upload:{original_filename}",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._records[dataset_id] = record
        return record

    def get_dataset(self, dataset_id: str) -> Optional[DatasetRecord]:
        """Retrieve a dataset record by ID."""
        return self._records.get(dataset_id)

    def list_datasets(self) -> list[DatasetRecord]:
        """List all stored datasets."""
        return list(self._records.values())

    @staticmethod
    def _safe_filename(original: str, fallback: str) -> str:
        """Sanitize a filename for safe storage."""
        # Remove path components, keep only the basename
        name = Path(original).name
        # Replace problematic characters
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
        return safe if safe else fallback


# Module-level singleton
dataset_manager = DatasetManager()
