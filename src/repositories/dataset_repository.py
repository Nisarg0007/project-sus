"""
Dataset Repository for SUS — Spike Understanding System.

Handles all database operations for the Dataset ORM model.
Follows the existing repository architecture:
- Accepts a Session through constructor
- Does NOT create or close sessions
- Does NOT commit — transaction ownership stays with the caller/service
- Uses SQLAlchemy 2.x query patterns
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database.models import Dataset

logger = logging.getLogger(__name__)


class DatasetRepository:
    """Data access layer for dataset metadata.

    Usage:
        repo = DatasetRepository(db_session)
        ds = repo.get_by_dataset_id("DS-ABC123")
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_dataset(
        self,
        *,
        dataset_id: str,
        original_filename: str,
        stored_path: str,
        data_source_type: str = "csv",
        row_count: Optional[int] = None,
        merchant_count: Optional[int] = None,
        min_transaction_date: Optional[str] = None,
        max_transaction_date: Optional[str] = None,
        validation_status: str = "pending",
        validation_message: Optional[str] = None,
    ) -> Dataset:
        """Persist a new Dataset record.

        Returns the created ORM object (with id populated after flush).
        Does NOT commit — caller must call session.commit().
        """
        ds = Dataset(
            dataset_id=dataset_id,
            original_filename=original_filename,
            stored_path=stored_path,
            data_source_type=data_source_type,
            row_count=row_count,
            merchant_count=merchant_count,
            min_transaction_date=min_transaction_date,
            max_transaction_date=max_transaction_date,
            validation_status=validation_status,
            validation_message=validation_message,
        )
        self.db.add(ds)
        self.db.flush()
        return ds

    def get_by_dataset_id(self, dataset_id: str) -> Optional[Dataset]:
        """Retrieve a Dataset by its business dataset_id.

        Returns None if not found.
        """
        stmt = select(Dataset).where(Dataset.dataset_id == dataset_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_datasets(self, *, limit: int = 100, offset: int = 0) -> list[Dataset]:
        """List all datasets, newest first."""
        stmt = (
            select(Dataset)
            .order_by(Dataset.created_at.desc(), Dataset.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_datasets(self) -> int:
        """Return total number of datasets."""
        stmt = select(func.count()).select_from(Dataset)
        return self.db.execute(stmt).scalar_one()

    def update_validation_status(
        self,
        dataset: Dataset,
        *,
        validation_status: str,
        validation_message: Optional[str] = None,
        row_count: Optional[int] = None,
        merchant_count: Optional[int] = None,
        min_transaction_date: Optional[str] = None,
        max_transaction_date: Optional[str] = None,
    ) -> Dataset:
        """Update validation metadata on a dataset.

        Does NOT commit — caller must commit.
        """
        dataset.validation_status = validation_status
        if validation_message is not None:
            dataset.validation_message = validation_message
        if row_count is not None:
            dataset.row_count = row_count
        if merchant_count is not None:
            dataset.merchant_count = merchant_count
        if min_transaction_date is not None:
            dataset.min_transaction_date = min_transaction_date
        if max_transaction_date is not None:
            dataset.max_transaction_date = max_transaction_date
        self.db.flush()
        return dataset
