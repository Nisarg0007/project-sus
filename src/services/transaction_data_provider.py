"""
Transaction Data Provider for SUS — Spike Understanding System.

Defines the abstraction layer between data sources and the ML pipeline.
The pipeline only sees pandas DataFrames; this layer handles how those
DataFrames are constructed from various input sources.

Design principles:
- Protocol-based: any provider that satisfies the interface works.
- The pipeline never calls pd.read_csv directly — it receives data through providers.
- Future providers (Razorpay API, database query, Kafka stream) only need
  to implement the protocol; no pipeline changes required.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required transaction columns for the ML pipeline
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = frozenset({
    "transaction_id",
    "merchant_id",
    "timestamp",
    "date",
    "customer_id",
    "amount",
    "payment_status",
})

# Optional columns — pipeline works without them but benefits from having them
OPTIONAL_COLUMNS = frozenset({
    "window_label",
    "customer_is_new",
    "sku_id",
    "is_retry",
    "device_id",
    "ip_id",
})


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------
class ValidationResult:
    """Result of transaction data validation."""

    def __init__(
        self,
        is_valid: bool,
        total_rows: int = 0,
        valid_rows: int = 0,
        errors: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ):
        self.is_valid = is_valid
        self.total_rows = total_rows
        self.valid_rows = valid_rows
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            **self.metadata,
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class TransactionDataProvider(ABC):
    """Protocol for transaction data sources.

    Any data source that can produce a pandas DataFrame of transactions
    and window labels can implement this protocol. The ML pipeline only
    consumes the DataFrames returned by load_transactions() and
    load_window_labels().
    """

    @abstractmethod
    def load_transactions(self) -> pd.DataFrame:
        """Load and return the transactions DataFrame.

        Must return a DataFrame with at minimum the columns in REQUIRED_COLUMNS.
        """

    @abstractmethod
    def load_window_labels(self) -> pd.DataFrame:
        """Load and return the window labels DataFrame.

        Must return a DataFrame with columns: merchant_id, date, window_label
        """

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Validate the data source without loading the full dataset.

        Returns a ValidationResult with counts, errors, and warnings.
        """

    @abstractmethod
    def get_metadata(self) -> dict:
        """Return metadata about this data source (name, path, row count, etc.)."""


# ---------------------------------------------------------------------------
# CSV Transaction Data Provider
# ---------------------------------------------------------------------------
class CSVTransactionDataProvider(TransactionDataProvider):
    """Provides transaction data from CSV files.

    This is the primary provider for local development and the initial
    production implementation. Accepts a path to a transactions CSV file
    and an optional path to window labels.

    If window_labels_path is not provided, the provider generates synthetic
    window labels from the transaction dates (each date becomes a window).
    """

    def __init__(
        self,
        transactions_path: str | Path,
        window_labels_path: str | Path | None = None,
        source_name: str | None = None,
    ):
        self.transactions_path = Path(transactions_path)
        self.window_labels_path = Path(window_labels_path) if window_labels_path else None
        self.source_name = source_name or f"csv:{self.transactions_path.name}"
        self._transactions: pd.DataFrame | None = None
        self._window_labels: pd.DataFrame | None = None

    def load_transactions(self) -> pd.DataFrame:
        """Load transactions from CSV."""
        if self._transactions is None:
            logger.info("Loading transactions from %s", self.transactions_path)
            self._transactions = pd.read_csv(self.transactions_path)
            logger.info("Loaded %d transactions", len(self._transactions))
        return self._transactions

    def load_window_labels(self) -> pd.DataFrame:
        """Load window labels from CSV, or generate from transaction dates."""
        if self._window_labels is None:
            if self.window_labels_path and self.window_labels_path.exists():
                logger.info("Loading window labels from %s", self.window_labels_path)
                self._window_labels = pd.read_csv(self.window_labels_path)
            else:
                logger.info("Generating window labels from transaction dates")
                self._window_labels = self._generate_window_labels()
            logger.info("Loaded %d window labels", len(self._window_labels))
        return self._window_labels

    def _generate_window_labels(self) -> pd.DataFrame:
        """Generate window labels from transaction dates.

        Creates one window per merchant per date. The window_label is
        set to 'unknown' since we don't have ground truth for uploaded data.
        """
        transactions = self.load_transactions()
        if "merchant_id" not in transactions.columns or "date" not in transactions.columns:
            raise ValueError(
                "Cannot generate window labels: transactions must have "
                "'merchant_id' and 'date' columns"
            )
        windows = (
            transactions[["merchant_id", "date"]]
            .drop_duplicates()
            .copy()
        )
        windows["window_label"] = "unknown"
        return windows

    def validate(self) -> ValidationResult:
        """Validate the transactions CSV without loading the full dataset.

        Checks:
        - File exists and is readable
        - Required columns present
        - Numeric fields (amount) are valid
        - Timestamps are parseable
        - Row count is non-zero
        - Detects missing/invalid rows
        """
        errors: list[str] = []
        warnings: list[str] = []
        metadata: dict = {}

        # Check file exists
        if not self.transactions_path.exists():
            return ValidationResult(
                is_valid=False,
                errors=[f"File not found: {self.transactions_path}"],
            )

        try:
            # Read CSV with limited rows for fast validation, then full read for counts
            preview = pd.read_csv(self.transactions_path, nrows=1000)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to read CSV: {e}"],
            )

        # Check required columns
        present_cols = set(preview.columns)
        missing_cols = REQUIRED_COLUMNS - present_cols
        if missing_cols:
            errors.append(f"Missing required columns: {sorted(missing_cols)}")

        # Check optional columns
        missing_optional = OPTIONAL_COLUMNS - present_cols
        if missing_optional:
            warnings.append(f"Missing optional columns: {sorted(missing_optional)}")

        if errors:
            return ValidationResult(
                is_valid=False,
                total_rows=len(preview),
                errors=errors,
                warnings=warnings,
            )

        # Validate amount column
        if "amount" in present_cols:
            non_numeric = pd.to_numeric(preview["amount"], errors="coerce").isna().sum()
            if non_numeric > 0:
                errors.append(f"{non_numeric} rows have non-numeric 'amount' values")

        # Validate timestamps
        if "timestamp" in present_cols:
            try:
                pd.to_datetime(preview["timestamp"], errors="raise")
            except (ValueError, TypeError):
                # Try to identify bad rows
                parsed = pd.to_datetime(preview["timestamp"], errors="coerce")
                bad_count = parsed.isna().sum()
                if bad_count > 0:
                    errors.append(f"{bad_count} rows have unparseable 'timestamp' values")

        # Validate date column
        if "date" in present_cols:
            parsed_dates = pd.to_datetime(preview["date"], errors="coerce")
            bad_dates = parsed_dates.isna().sum()
            if bad_dates > 0:
                errors.append(f"{bad_dates} rows have unparseable 'date' values")

        # Check for empty/whitespace-only merchant_id
        if "merchant_id" in present_cols:
            merchant_col = preview["merchant_id"]
            blank_merchants = merchant_col.isna().sum() + (
                merchant_col.astype(str).str.strip().eq("").sum()
            )
            if blank_merchants > 0:
                errors.append(f"{blank_merchants} rows have empty 'merchant_id'")

        # Full row count (read only the first column for speed)
        try:
            total_rows = sum(1 for _ in open(self.transactions_path)) - 1  # minus header
        except Exception:
            total_rows = len(preview)

        # Compute metadata
        if "merchant_id" in present_cols:
            metadata["unique_merchants"] = int(preview["merchant_id"].nunique())
        if "date" in present_cols:
            try:
                dates = pd.to_datetime(preview["date"], errors="coerce").dropna()
                metadata["date_range_start"] = dates.min().isoformat() if len(dates) > 0 else None
                metadata["date_range_end"] = dates.max().isoformat() if len(dates) > 0 else None
            except Exception:
                pass
        if "amount" in present_cols:
            amounts = pd.to_numeric(preview["amount"], errors="coerce").dropna()
            metadata["amount_min"] = float(amounts.min()) if len(amounts) > 0 else None
            metadata["amount_max"] = float(amounts.max()) if len(amounts) > 0 else None

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            total_rows=total_rows,
            valid_rows=total_rows if is_valid else 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
        )

    def get_metadata(self) -> dict:
        """Return metadata about this CSV data source."""
        meta = {
            "source_type": "csv",
            "source_name": self.source_name,
            "transactions_path": str(self.transactions_path),
            "window_labels_path": str(self.window_labels_path) if self.window_labels_path else None,
        }
        if self.transactions_path.exists():
            try:
                df = pd.read_csv(self.transactions_path, nrows=0)
                meta["columns"] = list(df.columns)
            except Exception:
                pass
        return meta
