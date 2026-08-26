"""
Pipeline Data Provider for SUS — Spike Understanding System.

Runs the ML pipeline once and caches results in memory so multiple
endpoints can serve data without redundant pipeline execution.

This is a temporary solution appropriate for the CSV-backed architecture.
When a database is added, this will be replaced by proper repository queries.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd

from src.config import settings
from src.pipeline import get_pipeline_summary, run_pipeline
from src.spike_detector import DEFAULT_Z_THRESHOLD, MIN_HISTORY_DAYS

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300


class PipelineDataCache:
    """In-memory cache for pipeline execution results."""

    def __init__(self):
        self._results: Optional[pd.DataFrame] = None
        self._timestamp: float = 0

    def is_valid(self) -> bool:
        return (
            self._results is not None
            and (time.time() - self._timestamp) < _CACHE_TTL
        )

    def get(self) -> Optional[pd.DataFrame]:
        if self.is_valid():
            return self._results
        return None

    def set(self, results: pd.DataFrame) -> None:
        self._results = results
        self._timestamp = time.time()

    def invalidate(self) -> None:
        self._results = None
        self._timestamp = 0


# Module-level cache singleton
_cache = PipelineDataCache()


def get_pipeline_results(
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Get pipeline results, using cache when available.

    Args:
        force_refresh: If True, re-run the pipeline regardless of cache.

    Returns:
        DataFrame with pipeline results for all merchants.
    """
    if not force_refresh and _cache.is_valid():
        logger.debug("Returning cached pipeline results")
        return _cache.get()  # type: ignore

    logger.info("Running pipeline (cache miss or forced refresh)...")
    transactions = pd.read_csv(settings.raw_data_dir + "/transactions.csv")
    window_labels = pd.read_csv(settings.raw_data_dir + "/window_labels.csv")

    results = run_pipeline(
        transactions,
        window_labels,
        z_threshold=settings.default_z_threshold,
        min_history_days=settings.default_min_history_days,
    )

    _cache.set(results)
    logger.info("Pipeline results cached (%d rows)", len(results))
    return results


def get_merchant_ids() -> list[str]:
    """Get all unique merchant IDs from the dataset."""
    results = get_pipeline_results()
    return sorted(results["merchant_id"].unique().tolist())


def get_pipeline_summary_data() -> dict:
    """Get aggregate pipeline summary statistics."""
    results = get_pipeline_results()
    return get_pipeline_summary(results)


def invalidate_cache() -> None:
    """Force cache invalidation."""
    _cache.invalidate()
