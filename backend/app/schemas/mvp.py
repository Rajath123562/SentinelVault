"""Pydantic schemas for HOTFIX MVP endpoints."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    mfa_code: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    username: str
    user_id: Optional[str] = None
    role: str
    permissions: Optional[List[str]] = None
    expires_at: str
    mfa_active: Optional[bool] = False


class UserResponse(BaseModel):
    username: str
    user_id: Optional[str] = None
    role: str
    permissions: Optional[List[str]] = None
    expires_at: str
    mfa_active: Optional[bool] = False


class MFAEnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str
    recovery_codes: List[str]
    notice: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class MFAVerifyResponse(BaseModel):
    status: str
    mfa_enabled: bool
    notice: str


class SessionRevokeRequest(BaseModel):
    token: str
    reason: Optional[str] = "Administrative revocation"


class SessionRevokeResponse(BaseModel):
    revoked: bool
    message: str


class SecurityEventSchema(BaseModel):
    event_id: str
    event_type: str
    outcome: str
    actor: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    source_ip: Optional[str] = None
    details: Optional[str] = None
    timestamp: str


class DatasetSummaryResponse(BaseModel):
    dataset_id: str
    title: str
    version: str
    is_official_dataset: bool
    privacy_unit: str
    description: str
    approved_fields: Dict[str, List[str]]
    total_records: int


class QueryPreviewRequest(BaseModel):
    dataset_id: str
    field: str
    operator: str = "equals"
    value: Any
    epsilon: float


class QueryPreviewResponse(BaseModel):
    is_valid: bool = True
    dataset_id: str
    field: str
    operator: str
    value: Any
    epsilon: float
    query_fingerprint: str
    estimated_privacy_cost: float
    current_remaining_budget: float
    is_budget_sufficient: bool
    is_cached_release_available: bool
    policy_status: str
    privacy_unit: Optional[str] = "patient_id"
    global_sensitivity: Optional[float] = 1.0
    logical_query: Optional[str] = ""


class QueryRunRequest(BaseModel):
    dataset_id: str
    field: str
    operator: str = "equals"
    value: Any
    epsilon: float
    idempotency_key: Optional[str] = None


class PrivacyReceiptSchema(BaseModel):
    receipt_id: str
    release_id: str
    user_id: str
    dataset_id: str
    dataset_version: str
    query_fingerprint: str
    query_description: str
    mechanism: str
    epsilon_spent: float
    cumulative_epsilon: float
    remaining_budget: float
    policy_check_status: str
    audit_entry_hash: str
    signature: str
    receipt_hash: Optional[str] = ""
    key_id: Optional[str] = "ED25519-ENCLAVE-2026-V1"
    schema_version: Optional[str] = "1.0.0"
    is_revoked: Optional[int] = 0
    revoked_reason: Optional[str] = None
    revoked_at: Optional[str] = None
    timestamp: str


class ReceiptVerificationChecksSchema(BaseModel):
    receipt_found: bool
    schema_valid: bool
    not_revoked: bool
    hash_match: bool
    signature_valid: bool
    key_trusted: bool
    release_linked: bool
    audit_linked: bool


class ReceiptVerificationResponse(BaseModel):
    receipt_id: str
    is_valid: bool
    verification_status: str
    checks: ReceiptVerificationChecksSchema
    key_id: str
    algorithm: str = "Ed25519 + SHA-256"
    timestamp: Optional[str] = None
    error_message: Optional[str] = None
    receipt_data: Optional[PrivacyReceiptSchema] = None


class ReceiptListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    receipts: List[PrivacyReceiptSchema]


class AuditEntrySchema(BaseModel):
    entry_id: int
    event_id: str
    actor: str
    dataset_scope: str
    query_fingerprint: str
    privacy_expenditure_micro: int
    cumulative_expenditure_micro: int
    mechanism: str
    receipt_id: str
    prev_hash: str
    entry_hash: str
    signature: str
    created_at: str


class AuditEntryListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    entries: List[AuditEntrySchema]


class IncidentStatusResponse(BaseModel):
    current_state: str
    trigger_source: str
    reason: str
    updated_by: str
    updated_at: str
    releases_allowed: bool
    max_permitted_epsilon: float
    status_badge: str


class IncidentTransitionRequest(BaseModel):
    new_state: str = Field(..., description="Target state: NORMAL, RESTRICTED, or RELEASES_DISABLED")
    reason: str = Field(..., min_length=10, description="Mandatory audit justification for incident transition")


class AlertDetailSchema(BaseModel):
    alert_id: str
    rule_id: str
    title: str
    severity: str
    status: str
    actor: Optional[str] = None
    resource: Optional[str] = None
    details: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: str
    updated_at: str


class AlertResolveRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=5, description="Mandatory resolution justification")
    status: Optional[str] = "RESOLVED"


class QueryRunResponse(BaseModel):
    release_id: str
    noisy_count: int
    epsilon_spent: float
    cumulative_epsilon: float
    remaining_budget: float
    is_cached: bool
    policy_check_status: str
    receipt: PrivacyReceiptSchema


class BudgetStatusResponse(BaseModel):
    dataset_id: str
    cap_epsilon: float
    spent_epsilon: float
    remaining_epsilon: float
    accounting_notice: str
    updated_at: str
    recent_releases: Optional[List[Dict[str, Any]]] = []


class AuditVerificationResponse(BaseModel):
    valid: bool
    total_entries: int
    verified_entries: int
    tamper_detected: bool
    error_message: Optional[str] = None
    broken_at_entry: Optional[int] = None
    algorithm: str = "SHA-256 + Ed25519"
    notice: str = "Tamper-evident verification of cryptographic hash chain and digital signatures"


class EvaluationStatusResponse(BaseModel):
    demonstration_benchmark_status: str = "AVAILABLE"
    official_accounting_spec_status: str = "DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED"
    official_empirical_risk_evaluation_status: str = "OFFICIAL EMPIRICAL RISK EVALUATION NOT CONFIGURED"
    notice: str = "Official Track 4 competition specification and attack harnesses not yet integrated."
    benchmark_report: Optional[Dict[str, Any]] = None


class UserListItemSchema(BaseModel):
    username: str
    user_id: str
    role: str
    status: str
    failed_attempts: int
    locked_until: Optional[str] = None
    created_at: str
    mfa_enabled: bool


class UserUnlockResponse(BaseModel):
    unlocked: bool
    username: str
    message: str


class SecurityAlertSchema(BaseModel):
    alert_id: str
    timestamp: str
    event_type: str
    severity: str
    outcome: str = "FLAGGED"
    actor: Optional[str] = None
    source_ip: Optional[str] = None
    details: Optional[str] = None
    status: Optional[str] = "OPEN"
    rule_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None

