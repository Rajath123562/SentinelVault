"""System and Health API Endpoints for HOTFIX."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from app.core.config import Settings, get_settings
from app.schemas.system import (
    HealthResponse,
    ReadinessResponse,
    SystemStatusResponse,
    CapabilityStatus,
)

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application liveness probe",
    description="Determines whether the FastAPI process is alive and able to accept requests."
)
async def get_health() -> HealthResponse:
    """Liveness probe. Does not imply privacy release readiness."""
    return HealthResponse(
        status="healthy",
        service="hotfix-backend",
        timestamp=datetime.now(timezone.utc)
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Application readiness probe",
    description="Reports application initialization while distinguishing application readiness from privacy readiness."
)
async def get_readiness(settings: Settings = Depends(get_settings)) -> ReadinessResponse:
    """
    Readiness probe.
    Explicitly separates application lifecycle readiness from privacy release readiness.
    """
    return ReadinessResponse(
        status="ready",
        phase=settings.app_config.app.phase,
        application_initialized=True,
        configuration_valid=True,
        privacy_release_ready=settings.is_privacy_release_ready,
        privacy_engine_implemented=False,
        official_spec_status=settings.spec_config.spec.status,
        evaluation_harness_status="UNAVAILABLE",
        release_disabled_reason=settings.app_config.privacy_release.disabled_reason
    )


@router.get(
    "/api/system/status",
    response_model=SystemStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Structured system status for frontend and monitoring",
    description="Returns verified status across application components, configuration, and planned capabilities."
)
async def get_system_status(settings: Settings = Depends(get_settings)) -> SystemStatusResponse:
    """
    Structured status payload reflecting genuine, verified application state.
    Does not falsely claim that later-phase modules are operational.
    """
    capabilities = [
        CapabilityStatus(
            id="CAP-01-FOUNDATION",
            name="Application Foundation & Lifecycle",
            status="IMPLEMENTED",
            phase="Phase 1",
            description="FastAPI application structure, routing, schemas, and lifecycle management."
        ),
        CapabilityStatus(
            id="CAP-02-CONFIG-GATES",
            name="Configuration & Fail-Closed Privacy Gates",
            status="IMPLEMENTED",
            phase="Phase 1",
            description="Validated YAML configuration, environment overrides, and fail-closed release controls."
        ),
        CapabilityStatus(
            id="CAP-03-AUTH-RBAC",
            name="Authentication & Role-Based Access Control",
            status="PLANNED",
            phase="Phase 2",
            description="Credential verification, temporary lockout after 5 failures, and role-based privilege checks."
        ),
        CapabilityStatus(
            id="CAP-04-DATASET-VALIDATION",
            name="Dataset Ingestion & Validation",
            status="PLANNED",
            phase="Phase 2",
            description="Validation of synthetic health and financial transaction records against schema definitions."
        ),
        CapabilityStatus(
            id="CAP-05-QUERY-INTERFACE",
            name="Restricted Analytical Query Interface",
            status="PLANNED",
            phase="Phase 2",
            description="Syntax and semantic validation preventing raw record extraction."
        ),
        CapabilityStatus(
            id="CAP-06-DP-ENGINE",
            name="Differential Privacy Engine",
            status="PLANNED",
            phase="Phase 3",
            description="Verified DP noise mechanisms conforming to official Track 4 specification."
        ),
        CapabilityStatus(
            id="CAP-07-BUDGET-LEDGER",
            name="Cumulative Privacy Budget Ledger",
            status="PLANNED",
            phase="Phase 3",
            description="Cumulative epsilon tracking (<= 5.0 cap) across repeated and related queries."
        ),
        CapabilityStatus(
            id="CAP-08-RISK-EVALUATION",
            name="Risk & Attack Evaluation Integration",
            status="PLANNED",
            phase="Phase 4",
            description="Re-identification and membership-inference attack resistance evaluation."
        ),
        CapabilityStatus(
            id="CAP-09-UTILITY-BENCHMARK",
            name="Utility Benchmarking & Prediction Task",
            status="PLANNED",
            phase="Phase 4",
            description="Empirical comparison against non-private baselines on approved analytical queries."
        ),
        CapabilityStatus(
            id="CAP-10-AUDIT-RECEIPTS",
            name="Signed Audit Evidence & Privacy Receipts",
            status="PLANNED",
            phase="Phase 5",
            description="Tamper-evident logs and verifiable Privacy Receipts for every released query."
        ),
    ]

    return SystemStatusResponse(
        project_name=settings.app_config.app.name,
        project_code=settings.app_config.app.short_name,
        team_id=settings.app_config.app.team_id,
        current_phase=settings.app_config.app.phase,
        application_health="HEALTHY",
        configuration_valid=True,
        privacy_releases_enabled=settings.is_privacy_release_ready,
        release_disabled_reason=settings.app_config.privacy_release.disabled_reason,
        official_spec_status=settings.spec_config.spec.status,
        official_harness_status="NOT_INTEGRATED",
        server_time=datetime.now(timezone.utc),
        capabilities=capabilities
    )

