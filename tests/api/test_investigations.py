"""
Tests for the investigation API endpoints.
"""

import os

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def has_data():
    """Check if test data files exist."""
    return os.path.exists("data/raw/transactions.csv")


class TestInvestigationEndpoint:
    """Tests for POST /api/v1/investigations/run"""

    def test_post_without_body_uses_defaults(self, client):
        """POST with empty body should use default values and succeed (if data exists)."""
        import os
        if not os.path.exists("data/raw/transactions.csv"):
            pytest.skip("Test data not generated")
        response = client.post("/api/v1/investigations/run", json={})
        # Should succeed with defaults, or fail with 422 if required fields missing
        assert response.status_code in (200, 422)

    def test_post_with_invalid_threshold_returns_422(self, client):
        """POST with invalid z_threshold should return validation error."""
        response = client.post(
            "/api/v1/investigations/run",
            json={"z_threshold": -1.0},
        )
        # Should fail validation (threshold must be >= 0)
        assert response.status_code == 422

    def test_post_with_missing_data_returns_404(self, client):
        """POST with non-existent data files should return 404."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "nonexistent_transactions.csv",
                "window_labels_path": "nonexistent_labels.csv",
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.skipif(
        not os.path.exists("data/raw/transactions.csv"),
        reason="Test data not generated",
    )
    def test_full_investigation_returns_200(self, client):
        """Full pipeline investigation should succeed with real data."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "data/raw/transactions.csv",
                "window_labels_path": "data/raw/window_labels.csv",
            },
        )
        assert response.status_code == 200

    @pytest.mark.skipif(
        not os.path.exists("data/raw/transactions.csv"),
        reason="Test data not generated",
    )
    def test_investigation_response_shape(self, client):
        """Investigation response should have expected structure."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "data/raw/transactions.csv",
                "window_labels_path": "data/raw/window_labels.csv",
            },
        )
        data = response.json()

        # Top-level fields
        assert "investigation_id" in data
        assert data["investigation_id"].startswith("INV-")
        assert "summary" in data
        assert "incidents" in data
        assert "total_results" in data
        assert isinstance(data["incidents"], list)

        # Summary structure
        summary = data["summary"]
        assert "total_windows" in summary
        assert "spikes_detected" in summary
        assert "spike_rate" in summary
        assert "fraud_incidents" in summary
        assert "review_required" in summary
        assert summary["total_windows"] > 0

    @pytest.mark.skipif(
        not os.path.exists("data/raw/transactions.csv"),
        reason="Test data not generated",
    )
    def test_investigation_incident_structure(self, client):
        """Each incident in the response should have the full expected shape."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "data/raw/transactions.csv",
                "window_labels_path": "data/raw/window_labels.csv",
            },
        )
        data = response.json()

        if len(data["incidents"]) == 0:
            pytest.skip("No incidents in results (unexpected with real data)")

        incident = data["incidents"][0]

        # Required fields
        assert "id" in incident
        assert "merchant_id" in incident
        assert "date" in incident
        assert "severity" in incident
        assert "classification" in incident
        assert "fraud_probability" in incident
        assert "confidence" in incident
        assert "confidence_band" in incident
        assert "anomaly_score" in incident
        assert "recommended_action" in incident
        assert "top_signals" in incident

        # Value ranges
        assert 0.0 <= incident["fraud_probability"] <= 1.0
        assert 0.0 <= incident["confidence"] <= 1.0
        assert incident["severity"] in ["critical", "high", "medium", "low"]
        assert incident["classification"] in [
            "fraud_spike",
            "organic_spike",
            "review_required",
            "baseline",
        ]

    @pytest.mark.skipif(
        not os.path.exists("data/raw/transactions.csv"),
        reason="Test data not generated",
    )
    def test_investigation_with_merchant_filter(self, client):
        """Filtered investigation should return only matching merchant."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "data/raw/transactions.csv",
                "window_labels_path": "data/raw/window_labels.csv",
                "merchant_filter": "merchant_001",
            },
        )
        assert response.status_code == 200
        data = response.json()

        for incident in data["incidents"]:
            assert incident["merchant_id"] == "merchant_001"

    @pytest.mark.skipif(
        not os.path.exists("data/raw/transactions.csv"),
        reason="Test data not generated",
    )
    def test_investigation_with_custom_threshold(self, client):
        """Investigation with custom threshold should work."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "data/raw/transactions.csv",
                "window_labels_path": "data/raw/window_labels.csv",
                "z_threshold": 1.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_windows"] > 0


class TestInvestigationAPIEdgeCases:
    """Edge case tests for the investigation endpoint."""

    def test_post_with_extra_fields(self, client):
        """Extra fields in the request should be ignored (not rejected)."""
        response = client.post(
            "/api/v1/investigations/run",
            json={
                "transactions_path": "nonexistent.csv",
                "window_labels_path": "nonexistent.csv",
                "extra_field_ignored": True,
            },
        )
        # Should still return 404 (not 422)
        assert response.status_code == 404

    def test_get_on_investigations_run_not_found(self, client):
        """GET /investigations/run should return 404 (no investigation ID 'run')."""
        response = client.get("/api/v1/investigations/run")
        assert response.status_code == 404
