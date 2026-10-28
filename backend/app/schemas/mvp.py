"""Pydantic schemas for HOTFIX MVP endpoints."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    expires_at: str


class UserResponse(BaseModel):
    username: str
    role: str
    expires_at: str


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
    timestamp: str


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
