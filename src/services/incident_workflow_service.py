"""
Incident Workflow Service for SUS — Spike Understanding System.

Orchestrates analyst workflow operations for persisted incidents:
- Retrieving incident details
- Updating workflow status, assignment, notes, resolution
- Recording status history audit trail
- Validating status transitions

This service separates analyst operational workflow from ML classification.
ML evidence is immutable; workflow state is analyst-managed.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import PersistedIncident
from src.repositories.incident_repository import IncidentRepository

logger = logging.getLogger(__name__)

# Sentinel value to explicitly clear a nullable field.
# Different from None which means "don't change".
_CLEAR_VALUE = "__CLEAR__"

# Allowed workflow status transitions.
# Keys are current status; values are allowed next statuses.
_VALID_TRANSITIONS: dict[str, list[str]] = {
    "open": ["investigating", "false_positive", "resolved"],
    "investigating": ["open", "false_positive", "resolved"],
    "resolved": ["open", "investigating"],
    "false_positive": ["open", "investigating"],
}

# Workflow statuses that can have a resolution
_RESOLUTION_ALLOWED_STATUSES = {"resolved", "false_positive"}


class IncidentWorkflowService:
    """Service for managing analyst workflow on persisted incidents.

    Responsibilities:
    - Retrieve incident details with workflow metadata
    - Validate and apply workflow updates
    - Create audit trail entries on status changes
    - Handle partial updates (notes, assignment, etc.)

    Usage:
        service = IncidentWorkflowService(db)
        result = service.update_incident(
            "INC-merchant_001-20250724",
            workflow_status="investigating",
            assigned_analyst="analyst_001",
        )
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._repo = IncidentRepository(db)

    def get_incident_detail(
        self, incident_id: str
    ) -> Optional[PersistedIncident]:
        """Retrieve a persisted incident with its status history.

        Returns the ORM object or None.
        """
        return self._repo.get_by_incident_id(incident_id, load_history=True)

    def update_incident(
        self,
        incident_id: str,
        *,
        workflow_status: Optional[str] = None,
        assigned_analyst: Optional[str] = None,
        analyst_notes: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> PersistedIncident:
        """Update an incident's workflow metadata.

        Validates status transitions, normalizes inputs, and creates
        a status history record if the workflow status changes.

        Args:
            incident_id: Business incident ID (e.g. "INC-merchant_001-20250724").
            workflow_status: New workflow status (if changing).
            assigned_analyst: Analyst to assign (None = clear).
            analyst_notes: Notes text (None = no change, "" = clear).
            resolution: Resolution outcome (if applicable).

        Returns:
            The updated PersistedIncident ORM object.

        Raises:
            ValueError: If incident not found.
            ValueError: If status transition is invalid.
            ValueError: If resolution is set on an incompatible status.
        """
        incident = self._repo.get_by_incident_id(incident_id)
        if incident is None:
            raise ValueError(f"Incident '{incident_id}' not found")

        old_status = incident.workflow_status

        # Validate status transition
        if workflow_status is not None and workflow_status != old_status:
            allowed = _VALID_TRANSITIONS.get(old_status, [])
            if workflow_status not in allowed:
                raise ValueError(
                    f"Invalid status transition: {old_status} → {workflow_status}. "
                    f"Allowed transitions: {allowed}"
                )

        # Validate resolution consistency
        effective_status = workflow_status or old_status
        if resolution is not None and effective_status not in _RESOLUTION_ALLOWED_STATUSES:
            raise ValueError(
                f"Resolution can only be set when status is 'resolved' or 'false_positive'. "
                f"Current/effective status: '{effective_status}'"
            )

        # Normalize inputs
        # - None means "don't change"
        # - _CLEAR_VALUE means "set to null"
        # - a string value means "set to this value"
        norm_analyst: str | None | object = assigned_analyst
        if isinstance(assigned_analyst, str) and not assigned_analyst.strip():
            norm_analyst = _CLEAR_VALUE  # empty string = clear
        elif isinstance(assigned_analyst, str):
            norm_analyst = assigned_analyst.strip() or _CLEAR_VALUE

        norm_notes: str | None | object = analyst_notes
        if analyst_notes is _CLEAR_VALUE or (isinstance(analyst_notes, str) and not analyst_notes.strip()):
            norm_notes = _CLEAR_VALUE
        elif isinstance(analyst_notes, str):
            norm_notes = analyst_notes.strip() or _CLEAR_VALUE

        norm_resolution: str | None | object = resolution
        if isinstance(resolution, str) and not resolution.strip():
            norm_resolution = _CLEAR_VALUE
        elif isinstance(resolution, str):
            norm_resolution = resolution.strip() or _CLEAR_VALUE

        # Create status history BEFORE updating the incident
        if workflow_status is not None and workflow_status != old_status:
            changed_by = None
            if isinstance(norm_analyst, str):
                changed_by = norm_analyst
            # Record the note text in the audit trail — but never record
            # the internal _CLEAR_VALUE sentinel.
            history_note = norm_notes if isinstance(norm_notes, str) else None
            self._repo.add_status_history(
                incident.id,
                old_status=old_status,
                new_status=workflow_status,
                changed_by=changed_by,
                note=history_note,
            )

        # Apply updates — _CLEAR_VALUE passes through to the repo
        self._repo.update_workflow(
            incident,
            workflow_status=workflow_status,
            assigned_analyst=norm_analyst,
            analyst_notes=norm_notes,
            resolution=norm_resolution,
        )

        self.db.commit()
        logger.info(
            "Incident %s updated: workflow=%s, analyst=%s",
            incident_id,
            incident.workflow_status,
            incident.assigned_analyst,
        )
        return incident

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
        created_from=None,
        created_to=None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> tuple[list[PersistedIncident], int]:
        """List persisted incidents with filters, sorting, and pagination.

        Returns (incidents, total_count).
        """
        filter_kwargs = dict(
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
        incidents = self._repo.list_incidents(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            **filter_kwargs,
        )
        total = self._repo.count_incidents(**filter_kwargs)
        return incidents, total


def _normalize_string(value: Optional[str]) -> Optional[str]:
    """Normalize a string input: strip whitespace, return None if empty."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


# Module-level singleton for use with dependency injection
incident_workflow_service = IncidentWorkflowService.__new__(IncidentWorkflowService)
