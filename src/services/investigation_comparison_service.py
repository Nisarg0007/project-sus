"""
Investigation Comparison Service for SUS — Spike Understanding System.

Read-only service that compares two persisted investigations.
Keeps comparison logic explicit and separate from retrieval.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.api.schemas.investigation_comparison import (
    IncidentChange,
    IncidentComparison,
    InvestigationComparisonResponse,
    InvestigationMeta,
    MetricComparison,
    SummaryComparison,
)
from src.repositories.investigation_repository import InvestigationRepository

logger = logging.getLogger(__name__)


def _metric(
    label: str,
    base: float,
    compare: float,
) -> MetricComparison:
    """Build a MetricComparison, handling division-by-zero safely."""
    absolute = compare - base
    pct: Optional[float] = None
    if base != 0:
        pct = round((absolute / base) * 100, 2)
    return MetricComparison(
        label=label,
        base_value=base,
        compare_value=compare,
        absolute_change=absolute,
        percentage_change=pct,
    )


def _compare_incidents(
    base_incidents: dict[str, dict],
    compare_incidents: dict[str, dict],
) -> IncidentComparison:
    """Compare two sets of incidents keyed by incident_id."""
    base_ids = set(base_incidents.keys())
    compare_ids = set(compare_incidents.keys())

    only_base = sorted(base_ids - compare_ids)
    only_compare = sorted(compare_ids - base_ids)
    shared = sorted(base_ids & compare_ids)

    changed: list[IncidentChange] = []
    unchanged = 0

    for iid in shared:
        b = base_incidents[iid]
        c = compare_incidents[iid]
        change = IncidentChange(
            incident_id=iid,
            merchant_id=b.get("merchant_id", ""),
        )
        has_change = False

        # Severity
        if b.get("severity") != c.get("severity"):
            change.severity_changed = True
            change.old_severity = b.get("severity")
            change.new_severity = c.get("severity")
            has_change = True

        # Classification
        if b.get("classification") != c.get("classification"):
            change.classification_changed = True
            change.old_classification = b.get("classification")
            change.new_classification = c.get("classification")
            has_change = True

        # Fraud probability
        bp = b.get("fraud_probability", 0.0)
        cp = c.get("fraud_probability", 0.0)
        if abs(bp - cp) > 1e-9:
            change.fraud_probability_changed = True
            change.old_fraud_probability = bp
            change.new_fraud_probability = cp
            has_change = True

        # Confidence
        bc = b.get("confidence", 0.0)
        cc = c.get("confidence", 0.0)
        if abs(bc - cc) > 1e-9:
            change.confidence_changed = True
            change.old_confidence = bc
            change.new_confidence = cc
            has_change = True

        # Anomaly score
        ba = b.get("anomaly_score", 0.0)
        ca = c.get("anomaly_score", 0.0)
        if abs(ba - ca) > 1e-9:
            change.anomaly_score_changed = True
            change.old_anomaly_score = ba
            change.new_anomaly_score = ca
            has_change = True

        # Predicted cause
        if b.get("predicted_cause") != c.get("predicted_cause"):
            change.predicted_cause_changed = True
            change.old_predicted_cause = b.get("predicted_cause")
            change.new_predicted_cause = c.get("predicted_cause")
            has_change = True

        if has_change:
            changed.append(change)
        else:
            unchanged += 1

    return IncidentComparison(
        only_in_base=only_base,
        only_in_compare=only_compare,
        in_both=shared,
        changed=changed,
        unchanged_count=unchanged,
    )


def _incident_to_dict(inc) -> dict:
    """Convert a PersistedIncident ORM object to a plain dict for comparison."""
    try:
        top_signals = json.loads(inc.top_signals_json)
    except (json.JSONDecodeError, TypeError):
        top_signals = []

    return {
        "incident_id": inc.incident_id,
        "merchant_id": inc.merchant_id,
        "severity": inc.severity,
        "classification": inc.classification,
        "fraud_probability": inc.fraud_probability,
        "confidence": inc.confidence,
        "anomaly_score": inc.anomaly_score,
        "predicted_cause": inc.predicted_cause,
        "top_signals": top_signals,
    }


class InvestigationComparisonService:
    """Read-only comparison of two persisted investigations."""

    def compare(
        self,
        db: Session,
        *,
        base_id: str,
        compare_id: str,
    ) -> InvestigationComparisonResponse:
        """Compare two investigations by their business IDs.

        Raises ValueError if either investigation is not found.
        """
        repo = InvestigationRepository(db)

        base_run = repo.get_by_investigation_id(base_id)
        if base_run is None:
            raise ValueError(f"Base investigation '{base_id}' not found")

        compare_run = repo.get_by_investigation_id(compare_id)
        if compare_run is None:
            raise ValueError(f"Comparison investigation '{compare_id}' not found")

        # Summary comparison
        summary = SummaryComparison(
            total_results=_metric(
                "Total Results", base_run.total_results, compare_run.total_results
            ),
            spikes_detected=_metric(
                "Spikes Detected", base_run.spikes_detected, compare_run.spikes_detected
            ),
            fraud_incidents=_metric(
                "Fraud Incidents", base_run.fraud_incidents, compare_run.fraud_incidents
            ),
            organic_incidents=_metric(
                "Organic Incidents", base_run.organic_incidents, compare_run.organic_incidents
            ),
            review_required=_metric(
                "Review Required", base_run.review_required, compare_run.review_required
            ),
            baseline_windows=_metric(
                "Baseline Windows", base_run.baseline_windows, compare_run.baseline_windows
            ),
            spike_rate=_metric(
                "Spike Rate", base_run.spike_rate, compare_run.spike_rate
            ),
        )

        # Incident comparison
        base_incidents = {_incident_to_dict(i)["incident_id"]: _incident_to_dict(i) for i in base_run.incidents}
        compare_incidents = {_incident_to_dict(i)["incident_id"]: _incident_to_dict(i) for i in compare_run.incidents}
        incidents = _compare_incidents(base_incidents, compare_incidents)

        return InvestigationComparisonResponse(
            base=InvestigationMeta(
                investigation_id=base_run.investigation_id,
                created_at=base_run.created_at,
                status=base_run.status,
            ),
            compare=InvestigationMeta(
                investigation_id=compare_run.investigation_id,
                created_at=compare_run.created_at,
                status=compare_run.status,
            ),
            summary=summary,
            incidents=incidents,
        )


# Module-level singleton
investigation_comparison_service = InvestigationComparisonService()
