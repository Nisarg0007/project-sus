"""
Investigation endpoints for SUS — Spike Understanding System.

Provides endpoints for running pipeline investigations and retrieving
structured results.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.schemas.investigations import (
    InvestigationRequest,
    InvestigationResponse,
    IncidentResponse,
    PipelineSummary,
)
from src.config import settings
from src.database.session import get_db
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
