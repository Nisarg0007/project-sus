"""Merchant API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas.merchants import (
    MerchantListResponse,
    MerchantListItem,
    MerchantProfileResponse,
)
from src.services.merchant_service import (
    get_merchant_directory,
    get_merchant_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=MerchantListResponse)
async def list_merchants(
    search: str | None = Query(None, description="Search merchants by ID"),
    limit: int | None = Query(None, ge=1, le=100),
) -> MerchantListResponse:
    """Get the merchant directory.

    Returns a list of all monitored merchants with summary statistics.
    """
    merchants = get_merchant_directory()

    if search:
        merchants = [m for m in merchants if search.lower() in m["id"].lower()]

    if limit:
        merchants = merchants[:limit]

    items = [MerchantListItem(**m) for m in merchants]
    return MerchantListResponse(merchants=items, total=len(items))


@router.get("/{merchant_id}", response_model=MerchantProfileResponse)
async def get_merchant(merchant_id: str) -> MerchantProfileResponse:
    """Get detailed merchant profile.

    Returns full merchant profile with incident history.
    Returns 404 if merchant not found.
    """
    profile = get_merchant_profile(merchant_id)

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Merchant '{merchant_id}' not found",
        )

    return MerchantProfileResponse(**profile)
