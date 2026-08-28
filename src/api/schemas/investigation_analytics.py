"""
API schemas for investigation analytics endpoint.

Provides aggregate insights across persisted investigations:
- Overview statistics
- Status distribution
- Activity over time
- Top merchants
- Recent activity
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Period / date range
# ---------------------------------------------------------------------------

class AnalyticsPeriod(BaseModel):
    """The date range used for analytics computation."""

    created_from: Optional[datetime] = Field(None, description="Start of analysis window")
    created_to: Optional[datetime] = Field(None, description="End of analysis window")


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class AnalyticsOverview(BaseModel):
    """Aggregate totals across all matching investigations."""

    total_investigations: int = Field(0, description="Total investigation count")
    completed_investigations: int = Field(0, description="Investigations with status 'completed'")
    total_results: int = Field(0, description="Sum of all total_results across investigations")
    total_spikes_detected: int = Field(0, description="Sum of all spikes_detected")
    total_fraud_incidents: int = Field(0, description="Sum of all fraud_incidents")
    total_organic_incidents: int = Field(0, description="Sum of all organic_incidents")
    total_review_required: int = Field(0, description="Sum of all review_required")
    average_spike_rate: float = Field(0.0, description="Mean spike_rate across investigations")
    average_fraud_per_investigation: float = Field(
        0.0, description="Mean fraud_incidents per investigation"
    )


# ---------------------------------------------------------------------------
# Status distribution
# ---------------------------------------------------------------------------

class StatusCount(BaseModel):
    """A single status and its investigation count."""

    status: str = Field(..., description="Investigation status")
    count: int = Field(..., description="Number of investigations with this status")


# ---------------------------------------------------------------------------
# Activity over time
# ---------------------------------------------------------------------------

class ActivityDay(BaseModel):
    """Investigation activity aggregated by calendar day."""

    date: str = Field(..., description="Calendar date (YYYY-MM-DD)")
    investigations: int = Field(0, description="Number of investigations on this day")
    total_results: int = Field(0, description="Sum of total_results on this day")
    spikes_detected: int = Field(0, description="Sum of spikes_detected on this day")
    fraud_incidents: int = Field(0, description="Sum of fraud_incidents on this day")
    organic_incidents: int = Field(0, description="Sum of organic_incidents on this day")
    review_required: int = Field(0, description="Sum of review_required on this day")


# ---------------------------------------------------------------------------
# Top merchants
# ---------------------------------------------------------------------------

class MerchantAnalytics(BaseModel):
    """Aggregate metrics for a merchant_filter across investigations."""

    merchant_filter: str = Field(..., description="Merchant identifier")
    investigation_count: int = Field(0, description="Number of investigations for this merchant")
    total_spikes_detected: int = Field(0, description="Total spikes across investigations")
    total_fraud_incidents: int = Field(0, description="Total fraud incidents")


# ---------------------------------------------------------------------------
# Recent activity
# ---------------------------------------------------------------------------

class RecentInvestigation(BaseModel):
    """Compact representation of a recent investigation."""

    investigation_id: str = Field(..., description="Unique investigation identifier")
    created_at: datetime = Field(..., description="When the investigation was run")
    status: str = Field(..., description="Investigation run status")
    total_results: int = Field(0, description="Total windows processed")
    spikes_detected: int = Field(0, description="Spikes detected")
    fraud_incidents: int = Field(0, description="Fraud incidents")


# ---------------------------------------------------------------------------
# Full response
# ---------------------------------------------------------------------------

class InvestigationAnalyticsResponse(BaseModel):
    """Complete analytics response for persisted investigations."""

    period: AnalyticsPeriod = Field(
        default_factory=AnalyticsPeriod, description="Analysis date range"
    )
    overview: AnalyticsOverview = Field(
        default_factory=AnalyticsOverview, description="Aggregate overview"
    )
    status_distribution: list[StatusCount] = Field(
        default_factory=list, description="Investigation status breakdown"
    )
    activity_over_time: list[ActivityDay] = Field(
        default_factory=list, description="Daily investigation activity"
    )
    top_merchants: list[MerchantAnalytics] = Field(
        default_factory=list, description="Top merchants by investigation count"
    )
    recent_activity: list[RecentInvestigation] = Field(
        default_factory=list, description="Most recent investigations"
    )
