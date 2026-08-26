"""Activity API routes."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.api.schemas.activity import ActivityEventResponse, ActivityListResponse
from src.services.activity_service import get_activity_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/events", response_model=ActivityListResponse)
async def list_activity_events(
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(None, ge=1, le=500),
) -> ActivityListResponse:
    """Get activity events.

    Returns detected anomaly/spike events derived from the pipeline.
    """
    events = get_activity_events(
        merchant_id=merchant_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=limit,
    )

    items = [ActivityEventResponse(**e) for e in events]
    return ActivityListResponse(events=items, total=len(items))
