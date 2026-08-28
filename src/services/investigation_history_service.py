"""
Investigation History Service for SUS — Spike Understanding System.

Provides read-only access to persisted investigation runs and their incidents.
Acts as the orchestration layer between API routes and the repository.

Design principles:
- Read-only — no mutation of investigation or incident records.
- Converts ORM models to API response schemas.
- Handles JSON deserialization of top_signals.
- Returns clean API-ready Pydantic models.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.api.schemas.investigation_history import (
    InvestigationDetailResponse,
    InvestigationListItem,
    InvestigationListResponse,
    InvestigationSummary,
    PersistedIncidentResponse,
)
from src.repositories.investigation_repository import InvestigationRepository

logger = logging.getLogger(__name__)


class InvestigationHistoryService:
    """Read-only service for retrieving persisted investigations."""

    def __init__(self) -> None:
        pass

    def list_investigations(
        self,
        db: Session,
        *,
        limit: int = 20,
        offset: int = 0,
        investigation_id: Optional[str] = None,
        status: Optional[str] = None,
        merchant_filter: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> InvestigationListResponse:
        """Return a paginated list of investigation runs, newest first.

        Args:
            db: Active database session.
            limit: Maximum items per page (1–100).
            offset: Number of items to skip.
            investigation_id: Partial match filter on investigation ID.
            status: Exact match filter on run status.
            merchant_filter: Partial match filter on merchant filter field.
            created_from: Lower bound for created_at timestamp.
            created_to: Upper bound for created_at timestamp.

        Returns:
            Paginated list response with metadata.
        """
        repo = InvestigationRepository(db)

        filter_kwargs = dict(
            investigation_id=investigation_id,
            status=status,
            merchant_filter=merchant_filter,
            created_from=created_from,
            created_to=created_to,
        )

        total = repo.count_investigations(**filter_kwargs)
        runs = repo.list_investigations(limit=limit, offset=offset, **filter_kwargs)

        items = [
            InvestigationListItem(
                investigation_id=run.investigation_id,
                status=run.status,
                created_at=run.created_at,
                total_results=run.total_results,
                spikes_detected=run.spikes_detected,
                fraud_incidents=run.fraud_incidents,
                organic_incidents=run.organic_incidents,
                review_required=run.review_required,
                baseline_windows=run.baseline_windows,
                spike_rate=run.spike_rate,
                processing_note=run.processing_note,
            )
            for run in runs
        ]

        return InvestigationListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    def get_investigation_detail(
        self,
        db: Session,
        investigation_id: str,
    ) -> Optional[InvestigationDetailResponse]:
        """Return full detail of a persisted investigation.

        Args:
            db: Active database session.
            investigation_id: The business ID of the investigation.

        Returns:
            Full detail response, or None if not found.
        """
        repo = InvestigationRepository(db)
        run = repo.get_by_investigation_id(investigation_id)

        if run is None:
            return None

        summary = InvestigationSummary(
            total_results=run.total_results,
            spikes_detected=run.spikes_detected,
            fraud_incidents=run.fraud_incidents,
            organic_incidents=run.organic_incidents,
            review_required=run.review_required,
            baseline_windows=run.baseline_windows,
            spike_rate=run.spike_rate,
            processing_note=run.processing_note,
        )

        incidents = [
            self._convert_incident(inc) for inc in run.incidents
        ]

        return InvestigationDetailResponse(
            investigation_id=run.investigation_id,
            status=run.status,
            created_at=run.created_at,
            transactions_path=run.transactions_path,
            window_labels_path=run.window_labels_path,
            model_path=run.model_path,
            z_threshold=run.z_threshold,
            min_history_days=run.min_history_days,
            merchant_filter=run.merchant_filter,
            summary=summary,
            incidents=incidents,
        )

    @staticmethod
    def _convert_incident(orm_incident) -> PersistedIncidentResponse:
        """Convert a PersistedIncident ORM model to an API response model.

        Handles JSON deserialization of top_signals_json.
        """
        try:
            top_signals = json.loads(orm_incident.top_signals_json)
        except (json.JSONDecodeError, TypeError):
            top_signals = []

        return PersistedIncidentResponse(
            incident_id=orm_incident.incident_id,
            merchant_id=orm_incident.merchant_id,
            date=orm_incident.date,
            severity=orm_incident.severity,
            status=orm_incident.status,
            classification=orm_incident.classification,
            predicted_cause=orm_incident.predicted_cause,
            fraud_probability=orm_incident.fraud_probability,
            confidence=orm_incident.confidence,
            confidence_band=orm_incident.confidence_band,
            anomaly_score=orm_incident.anomaly_score,
            decision_reason=orm_incident.decision_reason,
            anomaly_summary=orm_incident.anomaly_summary,
            top_signals=top_signals,
            recommended_action=orm_incident.recommended_action,
            created_at=orm_incident.created_at,
        )


# Module-level singleton
investigation_history_service = InvestigationHistoryService()
