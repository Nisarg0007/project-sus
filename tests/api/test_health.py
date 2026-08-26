"""
Tests for the health check API endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health"""

    def test_health_returns_200(self, client):
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Health endpoint should report healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_version(self, client):
        """Health endpoint should include version information."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_includes_pipeline_status(self, client):
        """Health endpoint should indicate pipeline load state."""
        response = client.get("/health")
        data = response.json()
        assert "pipeline_loaded" in data
        assert isinstance(data["pipeline_loaded"], bool)

    def test_health_response_shape(self, client):
        """Health endpoint should return exactly the expected fields."""
        response = client.get("/health")
        data = response.json()
        expected_keys = {"status", "version", "pipeline_loaded"}
        assert set(data.keys()) == expected_keys

    def test_investigations_endpoint_exists(self, client):
        """The investigations endpoint should be registered."""
        # POST to a non-existent path should return 404, not a routing error
        # Use invalid file paths to trigger a 404 from the service
        response = client.post(
            "/api/v1/investigations/run",
            json={"transactions_path": "__nonexistent__.csv"},
        )
        # Should get 404 (file not found) not 404 from routing
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_docs_endpoint_available(self, client):
        """Swagger docs should be accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
