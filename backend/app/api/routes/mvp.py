"""FastAPI MVP API Routes for HOTFIX Gateway."""

import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from app.db.connection import get_connection, record_security_event_db
from app.services.auth_service import (
    login_user,
    logout_user,
    get_session_user,
    has_permission,
    enroll_mfa_for_user,
    confirm_mfa_enrollment,
    revoke_session_administrative,
    AuthenticationError,
    AccountLockedError,
    RateLimitExceededError,
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
from app.services.crypto_audit import (
    verify_audit_ledger,
    verify_receipt_cryptographic,
    get_audit_entries,
)
from app.services.incident_service import (
    get_incident_status,
    transition_incident_state,
    list_security_alerts,
    get_security_alert_detail,
    acknowledge_security_alert,
    resolve_security_alert,
    IncidentStateError,
    ReleaseBlockedByIncidentError,
)
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
    ReceiptVerificationChecksSchema,
    ReceiptVerificationResponse,
    ReceiptListResponse,
    AuditEntrySchema,
    AuditEntryListResponse,
    IncidentStatusResponse,
    IncidentTransitionRequest,
    AlertDetailSchema,
    AlertResolveRequest,
    BudgetStatusResponse,
    AuditVerificationResponse,
    EvaluationStatusResponse,
    MFAEnrollResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    SessionRevokeRequest,
    SessionRevokeResponse,
    SecurityEventSchema,
    UserListItemSchema,
    UserUnlockResponse,
    SecurityAlertSchema,
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
        user = get_session_user(token)
        user["token"] = token
        return user
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


def require_permission(perm: str):
    """Factory creating dependency to enforce granular RBAC permissions."""
    def dependency(user: dict = Depends(get_current_user)):
        if not has_permission(user["role"], perm):
            conn = get_connection()
            try:
                record_security_event_db(
                    conn=conn,
                    event_type="UNAUTHORIZED_ACCESS",
                    outcome="DENIED",
                    actor=user.get("username", "unknown"),
                    source_ip="internal",
                    resource="rbac_guard",
                    action=f"REQUIRE_PERM_{perm}",
                    details=f"Forbidden: Role '{user.get('role')}' lacks permission '{perm}'"
                )
            finally:
                conn.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Role '{user['role']}' lacks permission '{perm}'"
            )
        return user
    return dependency


@router.post("/auth/login", response_model=LoginResponse, summary="User authentication")
async def login(req: LoginRequest, request: Request):
    """Authenticates user credentials and returns session token with 5-attempt lockout enforcement."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        session = login_user(req.username, req.password, client_ip=client_ip, mfa_code=req.mfa_code)
        return LoginResponse(**session)
    except AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e)) from e
    except RateLimitExceededError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


@router.post("/auth/logout", summary="End session")
async def logout(request: Request, authorization: Optional[str] = Header(None)):
    """Invalidates active session token."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        logout_user(token, client_ip=client_ip)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse, summary="Current user profile")
async def get_me(user: dict = Depends(get_current_user)):
    """Returns current authenticated identity and role."""
    return UserResponse(**user)


@router.post("/auth/mfa/enroll", response_model=MFAEnrollResponse, summary="Enroll in MFA")
async def enroll_mfa(user: dict = Depends(get_current_user)):
    """Generates a Base32 TOTP secret and recovery codes for the authenticated user."""
    try:
        data = enroll_mfa_for_user(user["username"])
        return MFAEnrollResponse(**data)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/auth/mfa/verify", response_model=MFAVerifyResponse, summary="Confirm MFA enrollment")
async def verify_mfa(req: MFAVerifyRequest, user: dict = Depends(get_current_user)):
    """Confirms MFA setup by validating the user's initial 6-digit TOTP code."""
    try:
        confirm_mfa_enrollment(user["username"], req.code)
        return MFAVerifyResponse(
            status="MFA_ENABLED",
            mfa_enabled=True,
            notice="Multi-factor authentication is now active on your account."
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/auth/sessions/revoke", response_model=SessionRevokeResponse, summary="Revoke session administratively")
async def revoke_session(req: SessionRevokeRequest, user: dict = Depends(require_permission("session.revoke"))):
    """Administratively terminates a session by token."""
    revoked = revoke_session_administrative(
        admin_actor=user["username"],
        target_token=req.token,
        reason=req.reason or "Administrative revocation"
    )
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target session not found or already revoked")
    return SessionRevokeResponse(revoked=True, message=f"Session revoked by {user['username']}")


@router.get("/security/events", response_model=List[SecurityEventSchema], summary="List security audit events")
async def get_security_events(
    limit: int = 50,
    user: dict = Depends(require_permission("security.events.read"))
):
    """Retrieves immutable security audit logs (restricted to data_steward, auditor, admin)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?",
            (min(max(limit, 1), 200),)
        ).fetchall()
        return [SecurityEventSchema(**dict(r)) for r in rows]
    finally:
        conn.close()


@router.get("/security/alerts", response_model=List[SecurityAlertSchema], summary="List security alerts")
async def get_security_alerts(
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(require_permission("security.events.read"))
):
    """Retrieves critical security alerts from persistent monitoring registry with fallback to security events."""
    alerts = list_security_alerts(status_filter=status_filter, severity_filter=severity_filter, limit=limit)
    if alerts:
        return [
            SecurityAlertSchema(
                alert_id=a["alert_id"],
                timestamp=a["created_at"],
                event_type=a["rule_id"],
                severity=a["severity"],
                outcome="FLAGGED",
                actor=a.get("actor"),
                source_ip=None,
                details=a.get("details"),
                status=a.get("status", "OPEN"),
                rule_id=a.get("rule_id"),
                evidence=a.get("evidence"),
                resolution_notes=a.get("resolution_notes")
            )
            for a in alerts
        ]

    # Fallback to events for backwards compatibility
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT event_id as alert_id, timestamp, event_type, 
                   CASE 
                       WHEN outcome IN ('DENIED', 'FAILURE') AND event_type LIKE '%LOCK%' THEN 'HIGH'
                       WHEN outcome IN ('DENIED', 'FAILURE') THEN 'MEDIUM'
                       ELSE 'LOW'
                   END as severity,
                   outcome, actor, source_ip, details
            FROM security_events 
            WHERE outcome IN ('DENIED', 'FAILURE', 'CHALLENGE')
            ORDER BY timestamp DESC LIMIT ?
            """,
            (min(max(limit, 1), 100),)
        ).fetchall()
        return [SecurityAlertSchema(**dict(r)) for r in rows]
    finally:
        conn.close()


@router.get("/security/alerts/{alert_id}", response_model=AlertDetailSchema, summary="Get alert detail")
async def get_security_alert_by_id(
    alert_id: str,
    user: dict = Depends(require_permission("security.events.read"))
):
    """Retrieves full detail and investigation evidence for a specific security alert."""
    alert = get_security_alert_detail(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found.")
    return AlertDetailSchema(**alert)


@router.post("/security/alerts/{alert_id}/acknowledge", response_model=AlertDetailSchema, summary="Acknowledge alert")
async def acknowledge_security_alert_endpoint(
    alert_id: str,
    user: dict = Depends(require_permission("security.events.read"))
):
    """Marks an open security alert as acknowledged by the current reviewer."""
    try:
        alert = acknowledge_security_alert(alert_id, actor=user["username"])
        return AlertDetailSchema(**alert)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/security/alerts/{alert_id}/resolve", response_model=AlertDetailSchema, summary="Resolve alert")
async def resolve_security_alert_endpoint(
    alert_id: str,
    req: AlertResolveRequest,
    user: dict = Depends(require_permission("security.policy.manage"))
):
    """Resolves a security alert with mandatory audit justification (Steward/Admin)."""
    try:
        alert = resolve_security_alert(
            alert_id=alert_id,
            actor=user["username"],
            resolution_notes=req.resolution_notes,
            status=req.status or "RESOLVED"
        )
        return AlertDetailSchema(**alert)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/users", response_model=List[UserListItemSchema], summary="List registered users")
async def list_users(user: dict = Depends(require_permission("user.manage"))):
    """Lists registered users and account status (admin/steward only)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT username, user_id, role, status, failed_attempts, locked_until, created_at, mfa_enabled FROM users ORDER BY created_at ASC"
        ).fetchall()
        return [
            UserListItemSchema(
                username=r["username"],
                user_id=r["user_id"] or r["username"],
                role=r["role"],
                status=r["status"],
                failed_attempts=r["failed_attempts"],
                locked_until=r["locked_until"],
                created_at=r["created_at"],
                mfa_enabled=bool(r["mfa_enabled"])
            )
            for r in rows
        ]
    finally:
        conn.close()


@router.post("/users/{target_username}/unlock", response_model=UserUnlockResponse, summary="Unlock locked account")
async def unlock_user(target_username: str, user: dict = Depends(require_permission("user.manage"))):
    """Administratively resets failed login attempts and lifts lockout."""
    norm_target = target_username.strip().lower()
    conn = get_connection()
    try:
        row = conn.execute("SELECT username, status FROM users WHERE username = ?", (norm_target,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{norm_target}' not found")
        
        with conn:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL, status = 'ACTIVE' WHERE username = ?",
                (norm_target,)
            )
        return UserUnlockResponse(
            unlocked=True,
            username=norm_target,
            message=f"Account '{norm_target}' has been successfully unlocked by {user['username']}."
        )
    finally:
        conn.close()



@router.get("/datasets", response_model=List[DatasetSummaryResponse], summary="List permitted datasets")
async def get_datasets(user: dict = Depends(require_permission("dataset.metadata.read"))):
    """Returns metadata and approved query categories for permitted datasets."""
    datasets = list_available_datasets()
    return [DatasetSummaryResponse(**d) for d in datasets]


@router.post("/queries/preview", response_model=QueryPreviewResponse, summary="Validate query & preview budget cost")
async def preview_query(req: QueryPreviewRequest, user: dict = Depends(require_permission("dataset.query.execute"))):
    """
    Validates query syntax and fields against dataset allowlists without releasing data.
    Returns estimated privacy cost and budget sufficiency.
    """
    try:
        meta = validate_query(req.dataset_id, req.field, req.operator, req.value, req.epsilon)
    except PolicyViolationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    privacy_unit = meta.get("privacy_unit", "patient_id" if req.dataset_id == "health" else "account_id")
    logical_query = f"SELECT COUNT_DISTINCT({privacy_unit}) AS noisy_count FROM {req.dataset_id}_vault WHERE {req.field} = '{req.value}'"

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
        is_valid=True,
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
        policy_status="POLICY_CHECK_PASSED" if is_sufficient else "PRIVACY_BUDGET_EXHAUSTED",
        privacy_unit=privacy_unit,
        global_sensitivity=1.0,
        logical_query=logical_query
    )


@router.post("/queries/run", response_model=QueryRunResponse, summary="Execute approved query with differential privacy")
async def run_query(req: QueryRunRequest, user: dict = Depends(require_permission("dataset.query.execute"))):
    """
    Executes an approved analytical count query, injects Laplace noise,
    records budget expenditure, and issues a cryptographically signed Privacy Receipt.
    """
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
    except ReleaseBlockedByIncidentError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Query release execution failed: {e}") from e


@router.get("/budget/{dataset_id}", response_model=BudgetStatusResponse, summary="Query dataset budget status")
async def get_budget(dataset_id: str, user: dict = Depends(require_permission("dataset.metadata.read"))):
    """Retrieves authoritative budget allowance and remaining balance."""
    try:
        data = get_budget_status(dataset_id)
        return BudgetStatusResponse(**data)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/receipts", response_model=ReceiptListResponse, summary="List authorized Privacy Receipts")
async def list_receipts(
    limit: int = 50,
    offset: int = 0,
    dataset_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Lists privacy receipts with object-level isolation (analysts see only own; auditors/stewards see all)."""
    has_broad_access = has_permission(user["role"], "receipt.read.authorized")
    conn = get_connection()
    try:
        query = "FROM privacy_receipts WHERE 1=1"
        params: List[Any] = []
        if not has_broad_access:
            query += " AND (user_id = ? OR user_id = ?)"
            params.extend([user["username"], user.get("user_id", "")])
        if dataset_id:
            query += " AND dataset_id = ?"
            params.append(dataset_id)

        count_sql = f"SELECT COUNT(*) as total {query}"
        total = conn.execute(count_sql, params).fetchone()["total"]

        data_sql = f"SELECT * {query} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        fetch_params = params + [min(max(limit, 1), 100), max(offset, 0)]
        rows = conn.execute(data_sql, fetch_params).fetchall()
        return ReceiptListResponse(
            total=total,
            limit=limit,
            offset=offset,
            receipts=[PrivacyReceiptSchema(**dict(r)) for r in rows]
        )
    finally:
        conn.close()


@router.get("/receipts/{receipt_id}", response_model=PrivacyReceiptSchema, summary="Retrieve a Privacy Receipt")
async def get_receipt(receipt_id: str, user: dict = Depends(get_current_user)):
    """Retrieves a previously issued Privacy Receipt by ID with object-level access gating."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM privacy_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Receipt '{receipt_id}' not found")

        # Object-level access control:
        # Stewards and Auditors have 'receipt.read.authorized' to inspect any receipt
        # Analysts have 'receipt.read.own' and can ONLY view their own receipts
        has_broad_access = has_permission(user["role"], "receipt.read.authorized")
        is_owner = (row["user_id"] == user["username"] or row["user_id"] == user.get("user_id"))

        if not has_broad_access and not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Analysts may only view receipts they generated. Receipt '{receipt_id}' belongs to another analyst."
            )

        return PrivacyReceiptSchema(**dict(row))
    finally:
        conn.close()


@router.post("/receipts/{receipt_id}/verify", response_model=ReceiptVerificationResponse, summary="Verify Privacy Receipt cryptographic integrity")
async def verify_receipt(receipt_id: str, user: dict = Depends(get_current_user)):
    """
    Cryptographically verifies a Privacy Receipt by checking canonical hash, Ed25519 signature,
    signing key trust status, release association, and audit ledger linkage.
    """
    conn = get_connection()
    try:
        row = conn.execute("SELECT user_id FROM privacy_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Privacy receipt '{receipt_id}' not found.")

        has_broad_access = has_permission(user["role"], "receipt.read.authorized")
        is_owner = (row["user_id"] == user["username"] or row["user_id"] == user.get("user_id"))
        if not has_broad_access and not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Analysts may only verify receipts they generated."
            )

        verification_result = verify_receipt_cryptographic(conn, receipt_id)
        return ReceiptVerificationResponse(
            receipt_id=verification_result["receipt_id"],
            is_valid=verification_result["is_valid"],
            verification_status=verification_result["verification_status"],
            checks=ReceiptVerificationChecksSchema(**verification_result["checks"]),
            key_id=verification_result["key_id"],
            algorithm=verification_result["algorithm"],
            timestamp=verification_result["timestamp"],
            error_message=verification_result["error_message"],
            receipt_data=PrivacyReceiptSchema(**verification_result["receipt_data"]) if verification_result.get("receipt_data") else None
        )
    finally:
        conn.close()


@router.get("/audit/entries", response_model=AuditEntryListResponse, summary="List immutable audit trail entries")
async def list_audit_entries(
    limit: int = 50,
    offset: int = 0,
    dataset_scope: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(require_permission("audit.verify"))
):
    """Returns paginated, searchable rows from the immutable audit log."""
    conn = get_connection()
    try:
        entries, total = get_audit_entries(conn, limit=limit, offset=offset, dataset_scope=dataset_scope, search=search)
        return AuditEntryListResponse(
            total=total,
            limit=limit,
            offset=offset,
            entries=[AuditEntrySchema(**e) for e in entries]
        )
    finally:
        conn.close()


@router.get("/incident/status", response_model=IncidentStatusResponse, summary="Get current gateway incident status")
async def get_incident(user: dict = Depends(get_current_user)):
    """Returns the authoritative gateway incident response status and release policy constraints."""
    status_data = get_incident_status()
    return IncidentStatusResponse(**status_data)


@router.post("/incident/transition", response_model=IncidentStatusResponse, summary="Execute incident state transition")
async def execute_incident_transition(
    req: IncidentTransitionRequest,
    user: dict = Depends(require_permission("security.policy.manage"))
):
    """Executes an authorized state transition in the incident response state machine (Admin/Steward)."""
    try:
        new_status = transition_incident_state(
            new_state=req.new_state,
            actor=user["username"],
            reason=req.reason,
            trigger_source=f"ADMIN_API_{user['role'].upper()}"
        )
        return IncidentStatusResponse(**new_status)
    except IncidentStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/audit/verify", response_model=AuditVerificationResponse, summary="Verify cryptographic audit log integrity")
async def verify_audit(user: dict = Depends(require_permission("audit.verify"))):
    """Verifies SHA-256 hash chaining, Ed25519 signatures, and accounting consistency across the audit log."""
    conn = get_connection()
    try:
        report = verify_audit_ledger(conn)
        return AuditVerificationResponse(**report)
    finally:
        conn.close()


@router.get("/evaluation/status", response_model=EvaluationStatusResponse, summary="Evaluation status")
async def get_evaluation_status(user: dict = Depends(require_permission("system.status.read"))):
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
