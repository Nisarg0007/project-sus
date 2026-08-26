"""
Health check endpoint for SUS — Spike Understanding System.

Provides a simple health check that verifies the service is running
and the ML pipeline is operational.
"""

from fastapi import APIRouter

from src.api.schemas.investigations import HealthResponse
from src.config import settings
from src.services.investigation_service import investigation_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Check service health and pipeline readiness.

    Returns healthy status with version and pipeline load state.
    """
    status_info = investigation_service.get_investigation_status()

    return HealthResponse(
        status="healthy",
        version=status_info["app_version"],
        pipeline_loaded=status_info["pipeline_ready"],
    )
