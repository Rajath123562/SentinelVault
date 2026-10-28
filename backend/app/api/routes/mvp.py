"""FastAPI MVP API Routes for HOTFIX Gateway."""

import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.db.connection import get_connection
from app.services.auth_service import (
    login_user,
    logout_user,
    get_session_user,
    AuthenticationError,
    AccountLockedError,
)
from app.services.query_engine import (
    list_available_datasets,
    validate_query,
    compute_query_fingerprint,
    compute_cache_key,
    execute_query_pipeline,
    get_budget_status,
    PolicyViolationError,
    BudgetExhaustedError,
    MECHANISM_NAME,
)
from app.services.crypto_audit import verify_audit_ledger
from app.schemas.mvp import (
    LoginRequest,
    LoginResponse,
    UserResponse,
    DatasetSummaryResponse,
    QueryPreviewRequest,
    QueryPreviewResponse,
    QueryRunRequest,
    QueryRunResponse,
    PrivacyReceiptSchema,
    BudgetStatusResponse,
    AuditVerificationResponse,
    EvaluationStatusResponse,
)

router = APIRouter(prefix="/api", tags=["MVP Gateway"])


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency extracting and validating Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Format: 'Bearer <token>'"
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        return get_session_user(token)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


@router.post("/auth/login", response_model=LoginResponse, summary="User authentication")
async def login(req: LoginRequest):
    """Authenticates user credentials and returns session token with 5-attempt lockout enforcement."""
    try:
        session = login_user(req.username, req.password)
        return LoginResponse(**session)
    except AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e)) from e
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


@router.post("/auth/logout", summary="End session")
async def logout(authorization: Optional[str] = Header(None)):
    """Invalidates active session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        logout_user(token)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse, summary="Current user profile")
async def get_me(user: dict = Depends(get_current_user)):
    """Returns current authenticated identity and role."""
    return UserResponse(**user)


@router.get("/datasets", response_model=List[DatasetSummaryResponse], summary="List permitted datasets")
async def get_datasets(user: dict = Depends(get_current_user)):
    """Returns metadata and approved query categories for permitted datasets."""
    datasets = list_available_datasets()
    return [DatasetSummaryResponse(**d) for d in datasets]


@router.post("/queries/preview", response_model=QueryPreviewResponse, summary="Validate query & preview budget cost")
async def preview_query(req: QueryPreviewRequest, user: dict = Depends(get_current_user)):
    """
    Validates query syntax and fields against dataset allowlists without releasing data.
    Returns estimated privacy cost and budget sufficiency.
    """
    try:
        validate_query(req.dataset_id, req.field, req.operator, req.value, req.epsilon)
    except PolicyViolationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    fingerprint = compute_query_fingerprint(req.dataset_id, req.field, req.operator, str(req.value))
    cache_key = compute_cache_key(req.dataset_id, fingerprint, req.epsilon, MECHANISM_NAME)
    budget = get_budget_status(req.dataset_id)

    # Check if a previously committed release exists for this exact query
    conn = get_connection()
    try:
        cached_row = conn.execute(
            "SELECT release_id FROM query_releases WHERE cache_key = ? LIMIT 1",
            (cache_key,)
        ).fetchone()
        is_cached = bool(cached_row)
    finally:
        conn.close()

    is_sufficient = budget["remaining_epsilon"] >= req.epsilon or is_cached

    return QueryPreviewResponse(
        dataset_id=req.dataset_id,
        field=req.field,
        operator=req.operator,
        value=req.value,
        epsilon=req.epsilon,
        query_fingerprint=fingerprint,
        estimated_privacy_cost=0.0 if is_cached else req.epsilon,
        current_remaining_budget=budget["remaining_epsilon"],
        is_budget_sufficient=is_sufficient,
        is_cached_release_available=is_cached,
        policy_status="POLICY_CHECK_PASSED" if is_sufficient else "PRIVACY_BUDGET_EXHAUSTED"
    )


@router.post("/queries/run", response_model=QueryRunResponse, summary="Execute approved query with differential privacy")
async def run_query(req: QueryRunRequest, user: dict = Depends(get_current_user)):
    """
    Executes an approved analytical count query, injects Laplace noise,
    records budget expenditure, and issues a cryptographically signed Privacy Receipt.
    """
    # Role restriction: Analysts, Stewards, and Auditors can run queries
    try:
        result = execute_query_pipeline(
            user_id=user["username"],
            user_role=user["role"],
            dataset_id=req.dataset_id,
            field=req.field,
            operator=req.operator,
            value=req.value,
            epsilon=req.epsilon,
            idempotency_key=req.idempotency_key
        )
        return QueryRunResponse(
            release_id=result["release_id"],
            noisy_count=result["noisy_count"],
            epsilon_spent=result["epsilon_spent"],
            cumulative_epsilon=result["cumulative_epsilon"],
            remaining_budget=result["remaining_budget"],
            is_cached=result["is_cached"],
            policy_check_status=result["policy_check_status"],
            receipt=PrivacyReceiptSchema(**result["receipt"])
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except PolicyViolationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except BudgetExhaustedError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Query release execution failed: {e}") from e


@router.get("/budget/{dataset_id}", response_model=BudgetStatusResponse, summary="Query dataset budget status")
async def get_budget(dataset_id: str, user: dict = Depends(get_current_user)):
    """Retrieves authoritative budget allowance and remaining balance."""
    try:
        data = get_budget_status(dataset_id)
        return BudgetStatusResponse(**data)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/receipts/{receipt_id}", response_model=PrivacyReceiptSchema, summary="Retrieve a Privacy Receipt")
async def get_receipt(receipt_id: str, user: dict = Depends(get_current_user)):
    """Retrieves a previously issued Privacy Receipt by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM privacy_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Receipt '{receipt_id}' not found")
        return PrivacyReceiptSchema(**dict(row))
    finally:
        conn.close()


@router.get("/audit/verify", response_model=AuditVerificationResponse, summary="Verify cryptographic audit log integrity")
async def verify_audit(user: dict = Depends(get_current_user)):
    """Verifies SHA-256 hash chaining, Ed25519 signatures, and accounting consistency across the audit log."""
    conn = get_connection()
    try:
        report = verify_audit_ledger(conn)
        return AuditVerificationResponse(**report)
    finally:
        conn.close()


@router.get("/evaluation/status", response_model=EvaluationStatusResponse, summary="Evaluation status")
async def get_evaluation_status(user: dict = Depends(get_current_user)):
    """Returns factual status regarding demonstration benchmark and unconfigured official harnesses."""
    report = None
    report_file = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "utility-benchmark-report.json"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                report = json.load(f)
        except Exception:
            report = None

    return EvaluationStatusResponse(benchmark_report=report)
