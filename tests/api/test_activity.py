"""Tests for activity API endpoint."""

import os
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


class TestActivityEvents:
    def test_list_events_returns_200(self, client):
        response = client.get("/api/v1/activity/events")
        assert response.status_code == 200

    def test_events_response_shape(self, client):
        data = client.get("/api/v1/activity/events").json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        assert data["total"] > 0

    def test_event_has_required_fields(self, client):
        events = client.get("/api/v1/activity/events").json()["events"]
        e = events[0]
        assert "id" in e
        assert "merchantId" in e
        assert "date" in e
        assert "status" in e
        assert "severity" in e
        assert "fraudProbability" in e

    def test_merchant_filter(self, client):
        response = client.get("/api/v1/activity/events?merchant_id=merchant_001")
        data = response.json()
        assert data["total"] > 0
        assert all(e["merchantId"] == "merchant_001" for e in data["events"])

    def test_status_filter(self, client):
        response = client.get("/api/v1/activity/events?status=fraud_spike")
        data = response.json()
        if data["total"] > 0:
            assert all(e["status"] == "fraud_spike" for e in data["events"])

    def test_limit_filter(self, client):
        response = client.get("/api/v1/activity/events?limit=5")
        data = response.json()
        assert len(data["events"]) == 5

    def test_nonexistent_merchant_returns_empty(self, client):
        response = client.get("/api/v1/activity/events?merchant_id=nonexistent")
        data = response.json()
        assert data["total"] == 0
        assert data["events"] == []
