"""Tests for merchant API endpoints."""

import os
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def has_data():
    return os.path.exists("data/raw/transactions.csv")


class TestMerchantDirectory:
    def test_list_merchants_returns_200(self, client):
        response = client.get("/api/v1/merchants")
        assert response.status_code == 200

    def test_list_merchants_response_shape(self, client):
        data = client.get("/api/v1/merchants").json()
        assert "merchants" in data
        assert "total" in data
        assert isinstance(data["merchants"], list)
        assert data["total"] > 0

    def test_merchant_item_has_required_fields(self, client):
        merchants = client.get("/api/v1/merchants").json()["merchants"]
        m = merchants[0]
        assert "id" in m
        assert "name" in m
        assert "dailyVolume" in m
        assert "riskLevel" in m
        assert "totalWindows" in m
        assert "fraudCount" in m

    def test_search_filter(self, client):
        response = client.get("/api/v1/merchants?search=merchant_001")
        data = response.json()
        assert data["total"] >= 1
        assert all("merchant_001" in m["id"] for m in data["merchants"])

    def test_limit_filter(self, client):
        response = client.get("/api/v1/merchants?limit=3")
        data = response.json()
        assert len(data["merchants"]) == 3


class TestMerchantProfile:
    def test_valid_merchant_returns_200(self, client):
        response = client.get("/api/v1/merchants/merchant_001")
        assert response.status_code == 200

    def test_profile_has_required_fields(self, client):
        data = client.get("/api/v1/merchants/merchant_001").json()
        assert data["id"] == "merchant_001"
        assert "riskPosture" in data
        assert "riskLabel" in data
        assert "summary" in data
        assert "totalWindows" in data
        assert "fraudCount" in data
        assert "incidents" in data
        assert isinstance(data["incidents"], list)

    def test_unknown_merchant_returns_404(self, client):
        response = client.get("/api/v1/merchants/nonexistent_merchant")
        assert response.status_code == 404

    def test_profile_incidents_have_structure(self, client):
        data = client.get("/api/v1/merchants/merchant_001").json()
        if len(data["incidents"]) > 0:
            inc = data["incidents"][0]
            assert "id" in inc
            assert "severity" in inc
            assert "fraudProbability" in inc

    def test_profile_incident_uses_classification_not_final_status(self, client):
        """Verify the contract: merchant incidents use 'classification', not 'finalStatus'."""
        data = client.get("/api/v1/merchants/merchant_001").json()
        if len(data["incidents"]) > 0:
            inc = data["incidents"][0]
            assert "classification" in inc, "Expected 'classification' field in merchant incident"
            assert "finalStatus" not in inc, "Unexpected 'finalStatus' field (should be 'classification')"
            assert inc["classification"] in ("fraud_spike", "organic_spike", "review_required")
