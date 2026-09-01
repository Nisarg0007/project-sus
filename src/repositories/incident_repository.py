"""
Incident Repository for SUS — Spike Understanding System.

Handles all database operations related to incident workflow management:
retrieving persisted incidents, updating analyst workflow metadata,
and managing the status history audit trail.

Design principles:
- Accepts a Session through constructor — does NOT create or close sessions.
- Does NOT commit — transaction ownership stays with the caller/service.
- Uses SQLAlchemy 2.x query patterns.
- Operates on ORM models directly — domain/API conversion happens elsewhere.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Select, select, func
from sqlalchemy.orm import Session, selectinload

from src.database.models import (
    IncidentStatusHistory,
    PersistedIncident,
)

logger = logging.getLogger(__name__)

# Sentinel for explicitly clearing a nullable field
_CLEAR_VALUE = "__CLEAR__"


class IncidentRepository:
    """Data access layer for incident workflow management.

    Usage:
        repo = IncidentRepository(db_session)
        incident = repo.get_by_incident_id("INC-merchant_001-20250724")
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_incident_id(
        self,
        incident_id: str,
        *,
        load_history: bool = False,
    ) -> Optional[PersistedIncident]:
        """Retrieve a PersistedIncident by its business incident_id.

        Args:
            incident_id: Business identifier (e.g. "INC-merchant_001-20250724").
            load_history: If True, eagerly load status_history.

        Returns the ORM object or None if not found.
        """
        options = []
        if load_history:
            options.append(
                selectinload(PersistedIncident.status_history)
            )
        stmt = select(PersistedIncident)
        if options:
            stmt = stmt.options(*options)
        stmt = stmt.where(PersistedIncident.incident_id == incident_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def update_workflow(
        self,
        incident: PersistedIncident,
        *,
        workflow_status: Optional[str] = None,
        assigned_analyst: Optional[str] | object = None,
        analyst_notes: Optional[str] = None,
        resolution: Optional[str] | object = None,
    ) -> PersistedIncident:
        """Update workflow metadata on an incident.

        - None means "don't change"
        - _CLEAR_VALUE means "set to null"
        - a string value means "set to this value"

        Does NOT commit — caller must commit.
        """
        now = datetime.now(timezone.utc)
        if workflow_status is not None:
            incident.workflow_status = workflow_status
        if assigned_analyst is _CLEAR_VALUE:
            incident.assigned_analyst = None
        elif assigned_analyst is not None:
            incident.assigned_analyst = assigned_analyst
        if analyst_notes is _CLEAR_VALUE:
            incident.analyst_notes = None
        elif analyst_notes is not None:
            incident.analyst_notes = analyst_notes
        if resolution is _CLEAR_VALUE:
            incident.resolution = None
        elif resolution is not None:
            incident.resolution = resolution
        incident.updated_at = now
        self.db.flush()
        return incident

    def add_status_history(
        self,
        incident_id: int,
        *,
        old_status: str,
        new_status: str,
        changed_by: Optional[str] = None,
        note: Optional[str] = None,
    ) -> IncidentStatusHistory:
        """Create a status history record for a workflow transition.

        Does NOT commit — caller must commit.
        """
        history = IncidentStatusHistory(
            incident_id=incident_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            note=note,
        )
        self.db.add(history)
        self.db.flush()
        return history

    def get_status_history(
        self,
        persisted_incident_id: int,
    ) -> list[IncidentStatusHistory]:
        """Return the status history for an incident, ordered by created_at.

        Uses the internal primary key (not business incident_id).
        """
        stmt = (
            select(IncidentStatusHistory)
            .where(IncidentStatusHistory.incident_id == persisted_incident_id)
            .order_by(IncidentStatusHistory.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ------------------------------------------------------------------
    # Filtering and sorting helpers
    # ------------------------------------------------------------------

    _SORT_COLUMNS = {
        "created_at": PersistedIncident.created_at,
        "updated_at": PersistedIncident.updated_at,
        "severity": PersistedIncident.severity,
        "fraud_probability": PersistedIncident.fraud_probability,
        "confidence": PersistedIncident.confidence,
    }

    def _apply_filters(
        self,
        stmt: Select,
        *,
        search: Optional[str] = None,
        merchant_id: Optional[str] = None,
        severity: Optional[str] = None,
        classification: Optional[str] = None,
        workflow_status: Optional[str] = None,
        assigned_analyst: Optional[str] = None,
        investigation_id: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> Select:
        """Apply optional filters to a SELECT on PersistedIncident."""
        if search:
            term = f"%{search}%"
            stmt = stmt.where(
                PersistedIncident.incident_id.ilike(term)
                | PersistedIncident.merchant_id.ilike(term)
            )
        if merchant_id:
            stmt = stmt.where(PersistedIncident.merchant_id == merchant_id)
        if severity:
            stmt = stmt.where(PersistedIncident.severity == severity)
        if classification:
            stmt = stmt.where(PersistedIncident.classification == classification)
        if workflow_status:
            stmt = stmt.where(PersistedIncident.workflow_status == workflow_status)
        if assigned_analyst:
            stmt = stmt.where(
                PersistedIncident.assigned_analyst.ilike(f"%{assigned_analyst}%")
            )
        if investigation_id:
            from src.database.models import InvestigationRun

            stmt = stmt.join(
                InvestigationRun,
                PersistedIncident.investigation_run_id == InvestigationRun.id,
            ).where(InvestigationRun.investigation_id == investigation_id)
        if created_from:
            stmt = stmt.where(PersistedIncident.created_at >= created_from)
        if created_to:
            stmt = stmt.where(PersistedIncident.created_at <= created_to)
        return stmt

    def _apply_sorting(
        self,
        stmt: Select,
        *,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Select:
        """Apply ordering with deterministic secondary sort."""
        if sort_by and sort_by in self._SORT_COLUMNS:
            column = self._SORT_COLUMNS[sort_by]
            if sort_order == "asc":
                stmt = stmt.order_by(column.asc(), PersistedIncident.id.desc())
            else:
                stmt = stmt.order_by(column.desc(), PersistedIncident.id.desc())
        else:
            stmt = stmt.order_by(
                PersistedIncident.created_at.desc(),
                PersistedIncident.id.desc(),
            )
        return stmt

    def list_incidents(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        merchant_id: Optional[str] = None,
        severity: Optional[str] = None,
        classification: Optional[str] = None,
        workflow_status: Optional[str] = None,
        assigned_analyst: Optional[str] = None,
        investigation_id: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> list[PersistedIncident]:
        """List persisted incidents with filters, sorting, and pagination."""
        stmt = select(PersistedIncident)
        stmt = self._apply_filters(
            stmt,
            search=search,
            merchant_id=merchant_id,
            severity=severity,
            classification=classification,
            workflow_status=workflow_status,
            assigned_analyst=assigned_analyst,
            investigation_id=investigation_id,
            created_from=created_from,
            created_to=created_to,
        )
        stmt = self._apply_sorting(stmt, sort_by=sort_by, sort_order=sort_order)
        return list(
            self.db.execute(stmt.offset(offset).limit(limit)).scalars().all()
        )

    def count_incidents(
        self,
        *,
        search: Optional[str] = None,
        merchant_id: Optional[str] = None,
        severity: Optional[str] = None,
        classification: Optional[str] = None,
        workflow_status: Optional[str] = None,
        assigned_analyst: Optional[str] = None,
        investigation_id: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> int:
        """Return total count of persisted incidents matching filters."""
        stmt = select(func.count()).select_from(PersistedIncident)
        stmt = self._apply_filters(
            stmt,
            search=search,
            merchant_id=merchant_id,
            severity=severity,
            classification=classification,
            workflow_status=workflow_status,
            assigned_analyst=assigned_analyst,
            investigation_id=investigation_id,
            created_from=created_from,
            created_to=created_to,
        )
        return self.db.execute(stmt).scalar_one()
