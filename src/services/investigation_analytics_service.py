"""
Investigation Analytics Service for SUS — Spike Understanding System.

Provides aggregate analytics across persisted investigations.
Orchestrates repository aggregation methods and builds API-ready responses.

Design principles:
- Read-only — no mutation of investigation or incident records.
- Delegates all database queries to InvestigationRepository.
- Handles empty database gracefully (zeros, empty arrays).
- No ML logic — purely derived from persisted data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.api.schemas.investigation_analytics import (
    ActivityDay,
    AnalyticsOverview,
    AnalyticsPeriod,
    InvestigationAnalyticsResponse,
    MerchantAnalytics,
    RecentInvestigation,
    StatusCount,
)
from src.repositories.investigation_repository import InvestigationRepository

logger = logging.getLogger(__name__)

# Number of recent investigations to include in analytics
RECENT_ACTIVITY_LIMIT = 10


class InvestigationAnalyticsService:
    """Read-only service for investigation analytics."""

    def get_analytics(
        self,
        db: Session,
        *,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> InvestigationAnalyticsResponse:
        """Compute and return full analytics response.

        Args:
            db: Active database session.
            created_from: Optional lower bound for investigation date.
            created_to: Optional upper bound for investigation date.

        Returns:
            Complete analytics response with overview, distributions,
            time series, merchant data, and recent activity.
        """
        repo = InvestigationRepository(db)

        # Overview
        overview_data = repo.get_analytics_overview(
            created_from=created_from, created_to=created_to,
        )
        overview = AnalyticsOverview(**overview_data)

        # Status distribution
        status_rows = repo.get_status_distribution(
            created_from=created_from, created_to=created_to,
        )
        status_distribution = [StatusCount(**row) for row in status_rows]

        # Activity over time
        activity_rows = repo.get_activity_over_time(
            created_from=created_from, created_to=created_to,
        )
        activity_over_time = [ActivityDay(**row) for row in activity_rows]

        # Top merchants
        merchant_rows = repo.get_top_merchants(
            limit=10, created_from=created_from, created_to=created_to,
        )
        top_merchants = [MerchantAnalytics(**row) for row in merchant_rows]

        # Recent activity
        recent_runs = repo.get_recent_investigations(
            limit=RECENT_ACTIVITY_LIMIT, created_from=created_from, created_to=created_to,
        )
        recent_activity = [
            RecentInvestigation(
                investigation_id=run.investigation_id,
                created_at=run.created_at,
                status=run.status,
                total_results=run.total_results,
                spikes_detected=run.spikes_detected,
                fraud_incidents=run.fraud_incidents,
            )
            for run in recent_runs
        ]

        return InvestigationAnalyticsResponse(
            period=AnalyticsPeriod(created_from=created_from, created_to=created_to),
            overview=overview,
            status_distribution=status_distribution,
            activity_over_time=activity_over_time,
            top_merchants=top_merchants,
            recent_activity=recent_activity,
        )


# Module-level singleton
investigation_analytics_service = InvestigationAnalyticsService()
