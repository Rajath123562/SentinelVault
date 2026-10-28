"""System and Health Pydantic Models for HOTFIX Gateway."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""
    status: str = Field(default="healthy", description="Application liveness indicator")
    service: str = Field(default="hotfix-backend", description="Service identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check"
    )


class ReadinessResponse(BaseModel):
    """Readiness probe response model distinguishing app readiness from privacy readiness."""
    status: str = Field(default="ready", description="Application readiness status")
    phase: str = Field(default="Phase 1", description="Current project phase")
    application_initialized: bool = Field(
        default=True,
        description="Whether core application modules are initialized"
    )
    configuration_valid: bool = Field(
        default=True,
        description="Whether configuration files were validated"
    )
    privacy_release_ready: bool = Field(
        default=False,
        description="Fail-closed indicator: false until privacy engine and official spec are verified"
    )
    privacy_engine_implemented: bool = Field(
        default=False,
        description="Differential privacy engine implementation status"
    )
    official_spec_status: str = Field(
        default="NOT_CONFIGURED",
        description="Status of official Track 4 privacy specification"
    )
    evaluation_harness_status: str = Field(
        default="UNAVAILABLE",
        description="Status of official evaluation harness integration"
    )
    release_disabled_reason: str = Field(
        default="Phase 1 foundation: Differential privacy engine and official accounting specification not yet configured",
        description="Explanation for why privacy releases are disabled"
    )


class CapabilityStatus(BaseModel):
    """Status description for a planned or implemented capability."""
    id: str = Field(..., description="Unique capability or requirement identifier")
    name: str = Field(..., description="Human-readable capability name")
    status: str = Field(..., description="Current status: IMPLEMENTED, PLANNED, BLOCKED, NOT_CONFIGURED")
    phase: str = Field(..., description="Target phase of capability implementation")
    description: str = Field(..., description="Brief description of capability scope")


class SystemStatusResponse(BaseModel):
    """Detailed system status payload for frontend and diagnostic monitoring."""
    project_name: str = Field(..., description="Full project name")
    project_code: str = Field(..., description="Short project acronym")
    team_id: str = Field(..., description="Official competition team ID")
    current_phase: str = Field(..., description="Current phase being executed")
    application_health: str = Field(default="HEALTHY", description="Operational health status")
    configuration_valid: bool = Field(default=True, description="Configuration validity status")
    privacy_releases_enabled: bool = Field(
        default=False,
        description="Whether differential privacy releases are permitted (fail-closed)"
    )
    release_disabled_reason: str = Field(
        ...,
        description="Factual reason why privacy releases are disabled"
    )
    official_spec_status: str = Field(..., description="State of official accounting specification")
    official_harness_status: str = Field(..., description="State of official evaluation harness")
    server_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current server UTC timestamp"
    )
    capabilities: List[CapabilityStatus] = Field(
        default_factory=list,
        description="Status matrix across all 10 planned core product capabilities"
    )


class ErrorResponse(BaseModel):
    """Sanitized, standardized error response structure."""
    error: str = Field(..., description="High-level error classification")
    detail: str = Field(..., description="Sanitized error description")
    code: str = Field(..., description="Machine-readable error code")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the error"
    )

