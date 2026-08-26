"""
FastAPI application for SUS — Spike Understanding System.

This is the main application entry point. It:
- Creates the FastAPI app with metadata
- Registers route handlers
- Configures middleware (CORS, error handling)
- Provides the /health endpoint at the root level

Start with:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info(
        "Starting %s v%s",
        settings.app_name,
        settings.app_version,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "SUS — Spike Understanding System API. "
            "Detects transaction anomalies, classifies causes, and generates "
            "actionable incident intelligence."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch-all handler to prevent raw stack traces in responses."""
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred. Check server logs for details.",
            },
        )

    # Register routes
    _register_routes(application)

    return application


def _register_routes(app: FastAPI) -> None:
    """Register all API route handlers."""
    from src.api.routes.health import router as health_router
    from src.api.routes.investigations import router as investigations_router
    from src.api.routes.merchants import router as merchants_router
    from src.api.routes.activity import router as activity_router
    from src.api.routes.incidents import router as incidents_router

    app.include_router(health_router)
    app.include_router(investigations_router, prefix=settings.api_prefix)
    app.include_router(merchants_router, prefix=settings.api_prefix)
    app.include_router(activity_router, prefix=settings.api_prefix)
    app.include_router(incidents_router, prefix=settings.api_prefix)


# ---------------------------------------------------------------------------
# Module-level app instance (for uvicorn)
# ---------------------------------------------------------------------------

app = create_app()
