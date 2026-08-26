"""API schemas for merchant endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MerchantListItem(BaseModel):
    """Merchant summary in the directory list."""

    id: str
    name: str
    daily_volume: int = Field(..., alias="dailyVolume")
    risk_level: str = Field(..., alias="riskLevel")
    total_windows: int = Field(0, alias="totalWindows")
    spikes_detected: int = Field(0, alias="spikesDetected")
    fraud_count: int = Field(0, alias="fraudCount")
    organic_count: int = Field(0, alias="organicCount")
    review_count: int = Field(0, alias="reviewCount")

    model_config = {"populate_by_name": True}


class MerchantIncidentSummary(BaseModel):
    """Incident summary within a merchant profile."""

    id: str
    merchant_id: str = Field(..., alias="merchantId")
    date: str
    severity: str
    status: str
    classification: str
    fraud_probability: float = Field(..., alias="fraudProbability")
    confidence: float
    confidence_band: str = Field(..., alias="confidenceBand")
    anomaly_score: float = Field(..., alias="anomalyScore")
    decision_reason: str = Field("", alias="decisionReason")
    anomaly_summary: str = Field("", alias="anomalySummary")
    top_signals: list[str] = Field(default_factory=list, alias="topSignals")
    recommended_action: str = Field("", alias="recommendedAction")

    model_config = {"populate_by_name": True}


class MerchantProfileResponse(BaseModel):
    """Detailed merchant profile."""

    id: str
    name: str
    daily_volume: int = Field(..., alias="dailyVolume")
    risk_level: str = Field(..., alias="riskLevel")
    risk_posture: str = Field(..., alias="riskPosture")
    risk_label: str = Field(..., alias="riskLabel")
    summary: str
    total_windows: int = Field(0, alias="totalWindows")
    spikes_detected: int = Field(0, alias="spikesDetected")
    fraud_count: int = Field(0, alias="fraudCount")
    organic_count: int = Field(0, alias="organicCount")
    review_count: int = Field(0, alias="reviewCount")
    incidents: list[MerchantIncidentSummary] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class MerchantListResponse(BaseModel):
    """Response for GET /api/v1/merchants"""

    merchants: list[MerchantListItem]
    total: int
