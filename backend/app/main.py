"""Main FastAPI application entrypoint for HOTFIX Privacy-by-Design Gateway."""

import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.api.routes.system import router as system_router
from app.schemas.system import ErrorResponse

logger = logging.getLogger("hotfix")


def create_application() -> FastAPI:
    """Application factory for HOTFIX Gateway."""
    settings = get_settings()

    # Configure root logging
    log_level = getattr(logging, settings.app_config.logging.level, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    app = FastAPI(
        title=settings.app_config.app.name,
        version=settings.app_config.app.version,
        description="Privacy-by-Design Analytics Gateway for sensitive health and financial records.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Sanitize and standardize HTTP exceptions
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP Error",
                detail=str(exc.detail),
                code=str(exc.status_code),
                timestamp=datetime.now(timezone.utc)
            ).model_dump(mode="json")
        )

    # Sanitize and standardize input validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="Validation Error",
                detail="The submitted request payload failed schema validation.",
                code="422",
                timestamp=datetime.now(timezone.utc)
            ).model_dump(mode="json")
        )

    # Catch-all exception handler enforcing safe, non-leaking responses (Test B09)
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled internal server exception", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal Server Error",
                detail="An internal server error occurred. Sensitive diagnostics are retained securely in server logs.",
                code="500",
                timestamp=datetime.now(timezone.utc)
            ).model_dump(mode="json")
        )

    # Fail-closed guard on any query release route during Phase 1
    @app.api_route(
        "/api/v1/query/release",
        methods=["GET", "POST"],
        status_code=status.HTTP_403_FORBIDDEN,
        summary="Protected analytical release route (disabled in Phase 1)",
        include_in_schema=False
    )
    async def blocked_release_route():
        """Fail-closed guard route: forbids data release while privacy controls are incomplete."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(
                error="Privacy Release Disabled",
                detail="Privacy releases are strictly disabled in Phase 1. The differential privacy engine and official accounting specification have not been integrated.",
                code="PRIVACY_RELEASE_DISABLED",
                timestamp=datetime.now(timezone.utc)
            ).model_dump(mode="json")
        )

    # Mount system routes
    app.include_router(system_router)

    return app


app = create_application()

