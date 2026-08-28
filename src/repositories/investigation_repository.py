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

from sqlalchemy import Select, select, func, case
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

    def get_incidents_for_investigation(self, investigation_id: str) -> list[PersistedIncident]:
        """Return all incidents belonging to an investigation.

        Returns an empty list if the investigation does not exist
        or has no incidents.
        """
        run = self.get_by_investigation_id(investigation_id)
        if run is None:
            return []
        return list(run.incidents)

    # ------------------------------------------------------------------
    # Analytics operations
    # ------------------------------------------------------------------

    def get_analytics_overview(
        self,
        *,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> dict:
        """Compute aggregate overview statistics across investigations.

        Returns a dict with total_investigations, completed_investigations,
        sum totals for results/spikes/incidents, and averages.
        All values are zero-safe (empty database returns zeros).
        """
        stmt = select(
            func.count().label("total_investigations"),
            func.sum(
                case((InvestigationRun.status == "completed", 1), else_=0)
            ).label("completed_investigations"),
            func.coalesce(func.sum(InvestigationRun.total_results), 0).label("total_results"),
            func.coalesce(func.sum(InvestigationRun.spikes_detected), 0).label("total_spikes_detected"),
            func.coalesce(func.sum(InvestigationRun.fraud_incidents), 0).label("total_fraud_incidents"),
            func.coalesce(func.sum(InvestigationRun.organic_incidents), 0).label("total_organic_incidents"),
            func.coalesce(func.sum(InvestigationRun.review_required), 0).label("total_review_required"),
            func.coalesce(func.avg(InvestigationRun.spike_rate), 0.0).label("average_spike_rate"),
            func.coalesce(func.avg(InvestigationRun.fraud_incidents), 0.0).label("average_fraud_per_investigation"),
        ).select_from(InvestigationRun)

        stmt = self._apply_date_filters(stmt, created_from=created_from, created_to=created_to)

        row = self.db.execute(stmt).one()
        return {
            "total_investigations": row.total_investigations,
            "completed_investigations": row.completed_investigations or 0,
            "total_results": int(row.total_results),
            "total_spikes_detected": int(row.total_spikes_detected),
            "total_fraud_incidents": int(row.total_fraud_incidents),
            "total_organic_incidents": int(row.total_organic_incidents),
            "total_review_required": int(row.total_review_required),
            "average_spike_rate": float(row.average_spike_rate),
            "average_fraud_per_investigation": float(row.average_fraud_per_investigation),
        }

    def get_status_distribution(
        self,
        *,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> list[dict]:
        """Return investigation counts grouped by status."""
        stmt = select(
            InvestigationRun.status,
            func.count().label("count"),
        ).select_from(InvestigationRun)
        stmt = self._apply_date_filters(stmt, created_from=created_from, created_to=created_to)
        stmt = stmt.group_by(InvestigationRun.status).order_by(InvestigationRun.status)

        rows = self.db.execute(stmt).all()
        return [{"status": row.status, "count": row.count} for row in rows]

    def get_activity_over_time(
        self,
        *,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> list[dict]:
        """Return investigation activity grouped by calendar day.

        Groups by date portion of created_at. Only includes days
        that have at least one investigation. Sorted chronologically.
        """
        # SQLite: use date() to extract the date portion
        stmt = select(
            func.date(InvestigationRun.created_at).label("date"),
            func.count().label("investigations"),
            func.coalesce(func.sum(InvestigationRun.total_results), 0).label("total_results"),
            func.coalesce(func.sum(InvestigationRun.spikes_detected), 0).label("spikes_detected"),
            func.coalesce(func.sum(InvestigationRun.fraud_incidents), 0).label("fraud_incidents"),
            func.coalesce(func.sum(InvestigationRun.organic_incidents), 0).label("organic_incidents"),
            func.coalesce(func.sum(InvestigationRun.review_required), 0).label("review_required"),
        ).select_from(InvestigationRun)
        stmt = self._apply_date_filters(stmt, created_from=created_from, created_to=created_to)
        stmt = (
            stmt.group_by(func.date(InvestigationRun.created_at))
            .order_by(func.date(InvestigationRun.created_at).asc())
        )

        rows = self.db.execute(stmt).all()
        return [
            {
                "date": row.date,
                "investigations": row.investigations,
                "total_results": int(row.total_results),
                "spikes_detected": int(row.spikes_detected),
                "fraud_incidents": int(row.fraud_incidents),
                "organic_incidents": int(row.organic_incidents),
                "review_required": int(row.review_required),
            }
            for row in rows
        ]

    def get_top_merchants(
        self,
        *,
        limit: int = 10,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> list[dict]:
        """Return top merchants by investigation count.

        Ignores investigations with null or empty merchant_filter.
        Returns at most ``limit`` results, ordered by investigation_count
        descending with deterministic secondary ordering.
        """
        stmt = (
            select(
                InvestigationRun.merchant_filter.label("merchant_filter"),
                func.count().label("investigation_count"),
                func.coalesce(func.sum(InvestigationRun.spikes_detected), 0).label("total_spikes_detected"),
                func.coalesce(func.sum(InvestigationRun.fraud_incidents), 0).label("total_fraud_incidents"),
            )
            .select_from(InvestigationRun)
            .where(InvestigationRun.merchant_filter.isnot(None))
            .where(InvestigationRun.merchant_filter != "")
        )
        stmt = self._apply_date_filters(stmt, created_from=created_from, created_to=created_to)
        stmt = (
            stmt.group_by(InvestigationRun.merchant_filter)
            .order_by(
                func.count().desc(),
                InvestigationRun.merchant_filter.asc(),
            )
            .limit(limit)
        )

        rows = self.db.execute(stmt).all()
        return [
            {
                "merchant_filter": row.merchant_filter,
                "investigation_count": row.investigation_count,
                "total_spikes_detected": int(row.total_spikes_detected),
                "total_fraud_incidents": int(row.total_fraud_incidents),
            }
            for row in rows
        ]

    def get_recent_investigations(
        self,
        *,
        limit: int = 10,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> list[InvestigationRun]:
        """Return the most recent investigation runs (newest first).

        Does not load incidents — lightweight for analytics display.
        """
        stmt = select(InvestigationRun)
        stmt = self._apply_date_filters(stmt, created_from=created_from, created_to=created_to)
        stmt = stmt.order_by(
            InvestigationRun.created_at.desc(),
            InvestigationRun.investigation_id.desc(),
        ).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def _apply_date_filters(
        self,
        stmt: Select,
        *,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> Select:
        """Apply date range filters to a SELECT statement."""
        if created_from:
            stmt = stmt.where(InvestigationRun.created_at >= created_from)
        if created_to:
            stmt = stmt.where(InvestigationRun.created_at <= created_to)
        return stmt
