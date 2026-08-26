"""Tests for incident list API endpoint."""

import os
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


class TestIncidentList:
    def test_list_incidents_returns_200(self, client):
        response = client.get("/api/v1/incidents")
        assert response.status_code == 200

    def test_incidents_response_shape(self, client):
        data = client.get("/api/v1/incidents").json()
        assert "incidents" in data
        assert "total" in data
        assert isinstance(data["incidents"], list)
        assert data["total"] > 0

    def test_incident_has_required_fields(self, client):
        incidents = client.get("/api/v1/incidents").json()["incidents"]
        inc = incidents[0]
        assert "id" in inc
        assert "merchantId" in inc
        assert "date" in inc
        assert "severity" in inc
        assert "classification" in inc
        assert "fraudProbability" in inc
        assert "recommendedAction" in inc

    def test_merchant_filter(self, client):
        response = client.get("/api/v1/incidents?merchant_id=merchant_001")
        data = response.json()
        assert data["total"] > 0
        assert all(i["merchantId"] == "merchant_001" for i in data["incidents"])

    def test_classification_filter(self, client):
        response = client.get("/api/v1/incidents?classification=fraud_spike")
        data = response.json()
        if data["total"] > 0:
            assert all(i["classification"] == "fraud_spike" for i in data["incidents"])

    def test_severity_filter(self, client):
        response = client.get("/api/v1/incidents?severity=critical")
        data = response.json()
        if data["total"] > 0:
            assert all(i["severity"] == "critical" for i in data["incidents"])

    def test_limit_filter(self, client):
        response = client.get("/api/v1/incidents?limit=3")
        data = response.json()
        assert len(data["incidents"]) == 3

    def test_only_fraud_and_review(self, client):
        """Incidents should only be fraud_spike or review_required."""
        data = client.get("/api/v1/incidents").json()
        for inc in data["incidents"]:
            assert inc["classification"] in ("fraud_spike", "review_required")
