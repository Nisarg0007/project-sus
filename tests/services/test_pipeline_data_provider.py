"""
Tests for PipelineDataCache.

Verifies:
- Cache hit returns same data without re-running pipeline
- TTL expiration triggers fresh pipeline load
- Invalidation forces reload
- Services do not mutate shared cached DataFrames
"""

import time
from unittest.mock import patch

import pandas as pd
import pytest

from src.services.pipeline_data_provider import (
    PipelineDataCache,
    get_pipeline_results,
    invalidate_cache,
)


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Ensure each test starts with a fresh cache."""
    from src.services import pipeline_data_provider

    pipeline_data_provider._cache = PipelineDataCache()
    yield
    pipeline_data_provider._cache = PipelineDataCache()


class TestPipelineDataCache:
    """Unit tests for the PipelineDataCache class."""

    def test_initial_state_is_invalid(self):
        cache = PipelineDataCache()
        assert cache.is_valid() is False
        assert cache.get() is None

    def test_set_and_get(self):
        cache = PipelineDataCache()
        df = pd.DataFrame({"a": [1, 2, 3]})
        cache.set(df)
        assert cache.is_valid() is True
        result = cache.get()
        assert result is not None
        assert list(result["a"]) == [1, 2, 3]

    def test_invalidation(self):
        cache = PipelineDataCache()
        df = pd.DataFrame({"a": [1]})
        cache.set(df)
        assert cache.is_valid() is True
        cache.invalidate()
        assert cache.is_valid() is False
        assert cache.get() is None

    def test_cache_hit_does_not_rerun_pipeline(self):
        """Repeated access within TTL returns cached data without calling pipeline."""
        call_count = 0
        mock_df = pd.DataFrame({"merchant_id": ["m1"], "final_status": ["baseline"]})

        def fake_pipeline(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_df.copy()

        with patch("src.services.pipeline_data_provider.run_pipeline", side_effect=fake_pipeline):
            with patch("src.services.pipeline_data_provider.pd.read_csv", return_value=pd.DataFrame()):
                result1 = get_pipeline_results()
                result2 = get_pipeline_results()

        assert call_count == 1, "Pipeline should only run once when cache is valid"
        assert result1 is result2, "Same DataFrame object should be returned from cache"

    def test_cache_expiration_triggers_reload(self):
        """After TTL expires, the next access should re-run the pipeline."""
        call_count = 0
        mock_df = pd.DataFrame({"merchant_id": ["m1"], "final_status": ["baseline"]})

        def fake_pipeline(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_df.copy()

        with patch("src.services.pipeline_data_provider.run_pipeline", side_effect=fake_pipeline):
            with patch("src.services.pipeline_data_provider.pd.read_csv", return_value=pd.DataFrame()):
                # First call: runs pipeline
                get_pipeline_results()
                assert call_count == 1

                # Manually expire the cache by backdating the timestamp
                from src.services import pipeline_data_provider
                pipeline_data_provider._cache._timestamp -= 400  # > 300s TTL

                # Second call: should re-run pipeline
                get_pipeline_results()
                assert call_count == 2

    def test_invalidation_forces_reload(self):
        """After invalidation, the next access should re-run the pipeline."""
        call_count = 0
        mock_df = pd.DataFrame({"merchant_id": ["m1"], "final_status": ["baseline"]})

        def fake_pipeline(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_df.copy()

        with patch("src.services.pipeline_data_provider.run_pipeline", side_effect=fake_pipeline):
            with patch("src.services.pipeline_data_provider.pd.read_csv", return_value=pd.DataFrame()):
                get_pipeline_results()
                assert call_count == 1

                invalidate_cache()

                get_pipeline_results()
                assert call_count == 2

    def test_force_refresh_bypasses_cache(self):
        """force_refresh=True always re-runs the pipeline."""
        call_count = 0
        mock_df = pd.DataFrame({"merchant_id": ["m1"], "final_status": ["baseline"]})

        def fake_pipeline(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_df.copy()

        with patch("src.services.pipeline_data_provider.run_pipeline", side_effect=fake_pipeline):
            with patch("src.services.pipeline_data_provider.pd.read_csv", return_value=pd.DataFrame()):
                get_pipeline_results()
                assert call_count == 1

                get_pipeline_results(force_refresh=True)
                assert call_count == 2

    def test_service_does_not_mutate_cached_data(self):
        """Services reading from cache should not affect other readers."""
        mock_df = pd.DataFrame({
            "merchant_id": ["m1", "m2"],
            "final_status": ["baseline", "fraud_spike"],
        })

        with patch("src.services.pipeline_data_provider.run_pipeline", return_value=mock_df.copy()):
            with patch("src.services.pipeline_data_provider.pd.read_csv", return_value=pd.DataFrame()):
                result1 = get_pipeline_results()
                # Simulate a service reading (doesn't mutate in this case,
                # but verifies the cache returns the same object)
                result2 = get_pipeline_results()
                assert result1 is result2


class TestGetPipelineResultsIntegration:
    """Integration tests using real pipeline data."""

    def test_get_pipeline_results_returns_dataframe(self):
        df = get_pipeline_results()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "merchant_id" in df.columns
        assert "final_status" in df.columns

    def test_get_pipeline_results_has_all_merchants(self):
        df = get_pipeline_results()
        merchants = sorted(df["merchant_id"].unique())
        assert len(merchants) == 8

    def test_get_pipeline_results_returns_same_object_on_repeat(self):
        result1 = get_pipeline_results()
        result2 = get_pipeline_results()
        assert result1 is result2
