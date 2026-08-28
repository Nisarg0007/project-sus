"""
Investigation Repository for SUS — Spike Understanding System.

Handles all database operations for InvestigationRun and PersistedIncident
ORM models. This is the ONLY place that should contain SQLAlchemy queries
for investigation data.

Design principles:
- Accepts a Session through constructor — does NOT create or close sessions.
- Does NOT commit — transaction ownership stays with the caller/service.
- Uses SQLAlchemy 2.x query patterns.
- Operates on ORM models directly — domain/API conversion happens elsewhere.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from src.database.models import InvestigationRun, PersistedIncident

logger = logging.getLogger(__name__)


class InvestigationRepository:
    """Data access layer for investigation runs and their incidents.

    Usage:
        repo = InvestigationRepository(db_session)
        run = repo.create_investigation(investigation_id="INV-ABC", ...)

    The caller is responsible for committing the session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Investigation Run operations
    # ------------------------------------------------------------------

    def create_investigation(
        self,
        *,
        investigation_id: str,
        status: str = "completed",
        transactions_path: str,
        window_labels_path: str,
        model_path: Optional[str] = None,
        z_threshold: float,
        min_history_days: int,
        merchant_filter: Optional[str] = None,
        total_results: int,
        spikes_detected: int,
        fraud_incidents: int,
        organic_incidents: int,
        review_required: int,
        baseline_windows: int,
        spike_rate: float,
        processing_note: str = "",
    ) -> InvestigationRun:
        """Persist a new InvestigationRun.

        Returns the created ORM object (with id populated after flush).
        Does NOT commit — caller must call session.commit().
        """
        run = InvestigationRun(
            investigation_id=investigation_id,
            status=status,
            transactions_path=transactions_path,
            window_labels_path=window_labels_path,
            model_path=model_path,
            z_threshold=z_threshold,
            min_history_days=min_history_days,
            merchant_filter=merchant_filter,
            total_results=total_results,
            spikes_detected=spikes_detected,
            fraud_incidents=fraud_incidents,
            organic_incidents=organic_incidents,
            review_required=review_required,
            baseline_windows=baseline_windows,
            spike_rate=spike_rate,
            processing_note=processing_note,
        )
        self.db.add(run)
        self.db.flush()  # Populate auto-generated id without committing
        return run

    def get_by_investigation_id(
        self, investigation_id: str
    ) -> Optional[InvestigationRun]:
        """Retrieve an InvestigationRun by its business ID.

        Incidents are eagerly loaded via selectin to avoid N+1 queries.
        Returns None if not found.
        """
        stmt = (
            select(InvestigationRun)
            .options(selectinload(InvestigationRun.incidents))
            .where(InvestigationRun.investigation_id == investigation_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def _apply_filters(
        self,
        stmt: Select,
        *,
        investigation_id: Optional[str] = None,
        status: Optional[str] = None,
        merchant_filter: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> Select:
        """Apply optional filters to a SELECT statement on InvestigationRun.

        This is the single source of filter logic used by both
        list_investigations() and count_investigations() to ensure
        consistent behavior.
        """
        if investigation_id:
            stmt = stmt.where(
                InvestigationRun.investigation_id.ilike(f"%{investigation_id}%")
            )
        if status:
            stmt = stmt.where(InvestigationRun.status == status)
        if merchant_filter:
            stmt = stmt.where(
                InvestigationRun.merchant_filter.ilike(f"%{merchant_filter}%")
            )
        if created_from:
            stmt = stmt.where(InvestigationRun.created_at >= created_from)
        if created_to:
            stmt = stmt.where(InvestigationRun.created_at <= created_to)
        return stmt

    # Allowed sort columns (maps string name → ORM column)
    _SORT_COLUMNS = {
        "created_at": InvestigationRun.created_at,
        "total_results": InvestigationRun.total_results,
        "spikes_detected": InvestigationRun.spikes_detected,
        "fraud_incidents": InvestigationRun.fraud_incidents,
        "spike_rate": InvestigationRun.spike_rate,
    }

    def _apply_sorting(
        self,
        stmt: Select,
        *,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Select:
        """Apply ordering to a SELECT statement.

        Defaults to created_at DESC (newest first) with a deterministic
        secondary sort on investigation_id DESC for stable pagination.
        """
        if sort_by and sort_by in self._SORT_COLUMNS:
            column = self._SORT_COLUMNS[sort_by]
            if sort_order == "asc":
                stmt = stmt.order_by(column.asc(), InvestigationRun.investigation_id.desc())
            else:
                stmt = stmt.order_by(column.desc(), InvestigationRun.investigation_id.desc())
        else:
            stmt = stmt.order_by(
                InvestigationRun.created_at.desc(),
                InvestigationRun.investigation_id.desc(),
            )
        return stmt

    def list_investigations(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        investigation_id: Optional[str] = None,
        status: Optional[str] = None,
        merchant_filter: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> list[InvestigationRun]:
        """List investigation runs with optional filters and sorting.

        Defaults to created_at DESC. Incidents are loaded via selectin.
        """
        stmt = select(InvestigationRun).options(
            selectinload(InvestigationRun.incidents)
        )
        stmt = self._apply_filters(
            stmt,
            investigation_id=investigation_id,
            status=status,
            merchant_filter=merchant_filter,
            created_from=created_from,
            created_to=created_to,
        )
        stmt = self._apply_sorting(stmt, sort_by=sort_by, sort_order=sort_order)
        return list(self.db.execute(stmt.offset(offset).limit(limit)).scalars().all())

    def count_investigations(
        self,
        *,
        investigation_id: Optional[str] = None,
        status: Optional[str] = None,
        merchant_filter: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> int:
        """Return the total number of persisted investigation runs matching filters."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(InvestigationRun)
        stmt = self._apply_filters(
            stmt,
            investigation_id=investigation_id,
            status=status,
            merchant_filter=merchant_filter,
            created_from=created_from,
            created_to=created_to,
        )
        return self.db.execute(stmt).scalar_one()

    # ------------------------------------------------------------------
    # Incident operations
    # ------------------------------------------------------------------

    def create_incident(
        self,
        *,
        investigation_run_id: int,
        incident_id: str,
        merchant_id: str,
        date: str,
        severity: str,
        status: str = "open",
        classification: str,
        predicted_cause: Optional[str] = None,
        fraud_probability: float,
        confidence: float,
        confidence_band: str,
        anomaly_score: float,
        decision_reason: str = "",
        anomaly_summary: str = "",
        top_signals_json: str = "[]",
        recommended_action: str = "",
    ) -> PersistedIncident:
        """Persist a new PersistedIncident linked to an InvestigationRun.

        Returns the created ORM object (with id populated after flush).
        Does NOT commit — caller must call session.commit().
        """
        incident = PersistedIncident(
            investigation_run_id=investigation_run_id,
            incident_id=incident_id,
            merchant_id=merchant_id,
            date=date,
            severity=severity,
            status=status,
            classification=classification,
            predicted_cause=predicted_cause,
            fraud_probability=fraud_probability,
            confidence=confidence,
            confidence_band=confidence_band,
            anomaly_score=anomaly_score,
            decision_reason=decision_reason,
            anomaly_summary=anomaly_summary,
            top_signals_json=top_signals_json,
            recommended_action=recommended_action,
        )
        self.db.add(incident)
        self.db.flush()
        return incident

    def get_incidents_for_investigation(
        self, investigation_id: str
    ) -> list[PersistedIncident]:
        """Return all incidents belonging to an investigation.

        Returns an empty list if the investigation does not exist
        or has no incidents.
        """
        run = self.get_by_investigation_id(investigation_id)
        if run is None:
            return []
        return list(run.incidents)
