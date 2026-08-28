"""
Investigation endpoints for SUS — Spike Understanding System.

Provides endpoints for:
- Running pipeline investigations (POST /run)
- Retrieving investigation history (GET /)
- Retrieving investigation detail (GET /{investigation_id})
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from src.api.schemas.investigation_comparison import (
    InvestigationComparisonResponse,
)
from src.api.schemas.investigation_history import (
    InvestigationDetailResponse,
    InvestigationListResponse,
)
from src.api.schemas.investigations import (
    InvestigationRequest,
    InvestigationResponse,
    IncidentResponse,
    PipelineSummary,
)
from src.config import settings
from src.database.session import get_db
from src.services.investigation_comparison_service import (
    investigation_comparison_service,
)
from src.services.investigation_history_service import (
    investigation_history_service,
)
from src.services.investigation_service import investigation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("/run", response_model=InvestigationResponse)
async def run_investigation(
    request: InvestigationRequest,
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    """Run a complete SUS pipeline investigation.

    Accepts paths to transaction data and window labels, runs the full
    detection → classification → explanation pipeline, and returns
    structured results with incidents.

    The endpoint delegates all ML logic to InvestigationService, which
    in turn calls the existing pipeline modules. No ML logic lives here.
    Results are persisted to the database when the pipeline succeeds.
    """
    try:
        result = investigation_service.run_investigation(
            transactions_path=request.transactions_path,
            window_labels_path=request.window_labels_path,
            model_path=request.model_path,
            z_threshold=request.z_threshold,
            min_history_days=settings.default_min_history_days,
            merchant_filter=request.merchant_filter,
            db=db,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found: {str(e)}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Pipeline processing error: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error during investigation")
        raise HTTPException(
            status_code=500,
            detail=f"Internal pipeline error: {str(e)}",
        )

    # Convert domain Incident models to API response models
    incident_responses = []
    for incident in result["incidents"]:
        incident_responses.append(
            IncidentResponse(
                id=incident.id,
                merchant_id=incident.merchant_id,
                date=incident.date,
                severity=incident.severity,
                status=incident.status,
                classification=incident.classification,
                fraud_probability=incident.fraud_probability,
                confidence=incident.confidence,
                confidence_band=incident.confidence_band,
                anomaly_score=incident.anomaly_score,
                decision_reason=incident.decision_reason,
                anomaly_summary=incident.anomaly_summary,
                top_signals=incident.top_signals,
                recommended_action=incident.recommended_action,
            )
        )

    return InvestigationResponse(
        investigation_id=result["investigation_id"],
        summary=result["summary"],
        incidents=incident_responses,
        total_results=result["total_results"],
        processing_note=result["processing_note"],
    )


# ---------------------------------------------------------------------------
# Investigation Rerun
# ---------------------------------------------------------------------------


@router.post(
    "/{investigation_id}/rerun",
    response_model=InvestigationResponse,
)
async def rerun_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    """Re-run a previously completed investigation with its stored configuration.

    Creates a completely new investigation with a new investigation_id.
    The original investigation is never modified.
    """
    try:
        result = investigation_service.rerun_investigation(
            investigation_id=investigation_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error during investigation rerun")
        raise HTTPException(
            status_code=500,
            detail=f"Internal pipeline error: {str(e)}",
        )

    incident_responses = []
    for incident in result["incidents"]:
        incident_responses.append(
            IncidentResponse(
                id=incident.id,
                merchant_id=incident.merchant_id,
                date=incident.date,
                severity=incident.severity,
                status=incident.status,
                classification=incident.classification,
                fraud_probability=incident.fraud_probability,
                confidence=incident.confidence,
                confidence_band=incident.confidence_band,
                anomaly_score=incident.anomaly_score,
                decision_reason=incident.decision_reason,
                anomaly_summary=incident.anomaly_summary,
                top_signals=incident.top_signals,
                recommended_action=incident.recommended_action,
            )
        )

    return InvestigationResponse(
        investigation_id=result["investigation_id"],
        summary=result["summary"],
        incidents=incident_responses,
        total_results=result["total_results"],
        processing_note=result["processing_note"],
    )


# ---------------------------------------------------------------------------
# Investigation Comparison
# ---------------------------------------------------------------------------


@router.get(
    "/compare",
    response_model=InvestigationComparisonResponse,
)
async def compare_investigations(
    base_id: str = Query(..., min_length=1, description="Base investigation ID"),
    compare_id: str = Query(..., min_length=1, description="Comparison investigation ID"),
    db: Session = Depends(get_db),
) -> InvestigationComparisonResponse:
    """Compare two persisted investigations side by side.

    Returns summary metric changes and incident-level differences.
    The original investigations are never modified.
    """
    if base_id == compare_id:
        raise HTTPException(
            status_code=422,
            detail="base_id and compare_id must be different",
        )

    try:
        return investigation_comparison_service.compare(
            db=db, base_id=base_id, compare_id=compare_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during investigation comparison")
        raise HTTPException(
            status_code=500,
            detail=f"Comparison error: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Investigation History
# ---------------------------------------------------------------------------


VALID_SORT_BY = {"created_at", "total_results", "spikes_detected", "fraud_incidents", "spike_rate"}
VALID_SORT_ORDER = {"asc", "desc"}


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    investigation_id: Optional[str] = Query(
        None, description="Partial match on investigation ID"
    ),
    status: Optional[str] = Query(
        None, description="Exact match on run status"
    ),
    merchant_filter: Optional[str] = Query(
        None, description="Partial match on merchant filter"
    ),
    created_from: Optional[datetime] = Query(
        None, description="Created on or after (ISO 8601)"
    ),
    created_to: Optional[datetime] = Query(
        None, description="Created on or before (ISO 8601)"
    ),
    sort_by: Optional[str] = Query(
        None,
        description=f"Column to sort by. Allowed: {', '.join(sorted(VALID_SORT_BY))}",
    ),
    sort_order: Optional[str] = Query(
        None,
        description="Sort direction: asc or desc",
    ),
) -> InvestigationListResponse:
    """List persisted investigation runs with pagination, filters, and sorting.

    Default ordering is newest first (created_at DESC).
    Does not include individual incidents — use the detail endpoint for that.
    """
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=422,
            detail="created_from must not be after created_to",
        )

    if sort_by is not None and sort_by not in VALID_SORT_BY:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort_by '{sort_by}'. Allowed: {', '.join(sorted(VALID_SORT_BY))}",
        )

    if sort_order is not None and sort_order not in VALID_SORT_ORDER:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort_order '{sort_order}'. Allowed: asc, desc",
        )

    return investigation_history_service.list_investigations(
        db=db,
        limit=limit,
        offset=offset,
        investigation_id=investigation_id,
        status=status,
        merchant_filter=merchant_filter,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationDetailResponse,
)
async def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
) -> InvestigationDetailResponse:
    """Retrieve a single persisted investigation with all its incidents.

    Returns full investigation details including input parameters,
    pipeline summary, and all persisted incidents with deserialized
    evidence signals.

    Returns 404 if the investigation does not exist.
    """
    result = investigation_history_service.get_investigation_detail(
        db=db, investigation_id=investigation_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation '{investigation_id}' not found",
        )

    return result
