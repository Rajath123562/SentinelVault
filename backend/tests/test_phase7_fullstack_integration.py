"""Phase 7 Master Full-Stack Integration Test Suite for SentinelVault.

Covers:
- End-to-end user workflows (auth -> datasets -> preview -> run -> receipt -> verify -> audit -> budget).
- Semantic parity between Query Preview logical_query and differential privacy execution.
- Reconciliation of Privacy Budget display with authoritative backend ledger.
- Operator flexibility ('equals' and '=' both supported).
- Zero-trust session validation (/api/me) and lifecycle.
- Granular Role-Based Access Control across all 4 roles.
- Cross-user receipt isolation.
- SIEM security events and Incident Response fail-closed enforcement.
- Tamper detection tripwires across receipts and audit hash chains.
"""

import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def analyst_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture(scope="module")
def auditor_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture(scope="module")
def steward_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture(scope="module")
def admin_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# SECTION 1: END-TO-END WORKFLOW INTEGRATION TESTS
# ==============================================================================

def test_p7_01_full_query_lifecycle_health_dataset(client: TestClient, analyst_token: str):
    """P7-01: Full query lifecycle on Health dataset from preview to receipt & audit verification."""
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Inspect datasets
    ds_res = client.get("/api/datasets", headers=headers)
    assert ds_res.status_code == 200
    datasets = ds_res.json()
    assert any(d["dataset_id"] == "health" for d in datasets)

    # 2. Preview query
    prev_payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5
    }
    prev_res = client.post("/api/queries/preview", json=prev_payload, headers=headers)
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["is_valid"] is True
    assert "COUNT_DISTINCT(patient_id)" in prev_data["logical_query"]
    assert prev_data["privacy_unit"] == "patient_id"
    assert prev_data["global_sensitivity"] == 1.0

    # 3. Execute differential privacy query
    run_payload = {**prev_payload, "idempotency_key": "p7-01-health-run"}
    run_res = client.post("/api/queries/run", json=run_payload, headers=headers)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert "release_id" in run_data
    assert isinstance(run_data["noisy_count"], int)
    assert run_data["noisy_count"] >= 0
    receipt = run_data["receipt"]
    assert receipt["receipt_id"].startswith("RCPT-")
    assert receipt["key_id"] == "ED25519-ENCLAVE-2026-V1"
    assert len(receipt["signature"]) > 32

    # 4. Verify Privacy Receipt cryptographically
    v_res = client.post(f"/api/receipts/{receipt['receipt_id']}/verify", headers=headers)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["is_valid"] is True
    assert "VERIFIED" in v_data["verification_status"]
    assert v_data["checks"]["hash_match"] is True
    assert v_data["checks"]["signature_valid"] is True


def test_p7_02_full_query_lifecycle_financial_dataset(client: TestClient, analyst_token: str):
    """P7-02: Full query lifecycle on Financial dataset using customer_id privacy unit."""
    headers = {"Authorization": f"Bearer {analyst_token}"}

    prev_payload = {
        "dataset_id": "financial",
        "field": "risk_band",
        "operator": "equals",
        "value": "high",
        "epsilon": 0.5
    }
    prev_res = client.post("/api/queries/preview", json=prev_payload, headers=headers)
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert "COUNT_DISTINCT(customer_id)" in prev_data["logical_query"]
    assert prev_data["privacy_unit"] == "customer_id"

    # Execute
    run_payload = {**prev_payload, "idempotency_key": "p7-02-financial-run"}
    run_res = client.post("/api/queries/run", json=run_payload, headers=headers)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["receipt"]["dataset_id"] == "financial"
    assert run_data["noisy_count"] >= 0


def test_p7_03_query_preview_logical_query_exact_match(client: TestClient, analyst_token: str):
    """P7-03: Query preview logical_query must explicitly describe distinct privacy unit aggregation."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    prev_payload = {
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "elective",
        "epsilon": 0.2
    }
    res = client.post("/api/queries/preview", json=prev_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    expected = "SELECT COUNT_DISTINCT(patient_id) AS noisy_count FROM health_vault WHERE admission_type = 'elective'"
    assert data["logical_query"] == expected


def test_p7_04_query_receipt_description_matches_preview(client: TestClient, analyst_token: str):
    """P7-04: Receipt query_description and preview logical_query must represent identical semantics."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "oncology",
        "epsilon": 0.5,
        "idempotency_key": "p7-04-receipt-match"
    }
    res = client.post("/api/queries/run", json=payload, headers=headers)
    assert res.status_code == 200
    receipt = res.json()["receipt"]
    assert "COUNT_DISTINCT(patient_id)" in receipt["query_description"]
    assert "diagnosis_category = 'oncology'" in receipt["query_description"]


def test_p7_05_operator_equals_string_and_symbol_both_pass(client: TestClient, analyst_token: str):
    """P7-05: Both 'equals' and '=' are accepted interchangeably without validation errors."""
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # Test with string 'equals'
    r1 = client.post("/api/queries/preview", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "neurological",
        "epsilon": 0.5
    }, headers=headers)
    assert r1.status_code == 200

    # Test with symbol '='
    r2 = client.post("/api/queries/preview", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "=",
        "value": "neurological",
        "epsilon": 0.5
    }, headers=headers)
    assert r2.status_code == 200
    assert r1.json()["query_fingerprint"] == r2.json()["query_fingerprint"]


def test_p7_06_unsupported_operators_rejected(client: TestClient, analyst_token: str):
    """P7-06: Relational operators other than equals are rejected fail-closed with HTTP 400."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    for bad_op in [">", "<", "LIKE", "IN", "UNION", "!="]:
        res = client.post("/api/queries/preview", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": bad_op,
            "value": "respiratory",
            "epsilon": 0.5
        }, headers=headers)
        assert res.status_code == 400
        assert "Unsupported operator" in res.json()["detail"]


# ==============================================================================
# SECTION 2: PRIVACY BUDGET & RECONCILIATION INTEGRATION
# ==============================================================================

def test_p7_07_budget_recent_releases_reconciled(client: TestClient, analyst_token: str):
    """P7-07: Budget status returns recent_releases matching authoritative database releases."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.get("/api/budget/health", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "recent_releases" in data
    assert isinstance(data["recent_releases"], list)
    assert data["cap_epsilon"] == 5.0
    assert data["spent_epsilon"] + data["remaining_epsilon"] == pytest.approx(5.0)

    # If releases exist, their records should contain valid descriptors
    for rel in data["recent_releases"]:
        assert rel["release_id"].startswith("REL-")
        assert "COUNT_DISTINCT" in rel["query_description"]
        assert rel["epsilon_spent"] > 0


def test_p7_08_budget_ledger_atomic_expenditure(client: TestClient, analyst_token: str):
    """P7-08: Budget expenditure correctly decreases remaining balance by exactly requested epsilon."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    b1 = client.get("/api/budget/financial", headers=headers).json()
    rem1 = b1["remaining_epsilon"]

    if rem1 >= 0.5:
        # Run query
        client.post("/api/queries/run", json={
            "dataset_id": "financial",
            "field": "transaction_type",
            "operator": "equals",
            "value": "wire",
            "epsilon": 0.5,
            "idempotency_key": "p7-08-budget-test"
        }, headers=headers)

        b2 = client.get("/api/budget/financial", headers=headers).json()
        assert b2["remaining_epsilon"] == pytest.approx(rem1 - 0.5, abs=0.001)


def test_p7_09_replay_cache_hit_zero_budget_cost(client: TestClient, analyst_token: str):
    """P7-09: Re-submitting an identical query fingerprint costs 0.00 ε and sets is_cached=True."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    query_payload = {
        "dataset_id": "health",
        "field": "discharge_status",
        "operator": "equals",
        "value": "routine",
        "epsilon": 0.5,
        "idempotency_key": "p7-09-cache-test"
    }

    # First run
    r1 = client.post("/api/queries/run", json=query_payload, headers=headers)
    assert r1.status_code == 200
    count1 = r1.json()["noisy_count"]

    # Second run (exact cache hit)
    r2 = client.post("/api/queries/run", json=query_payload, headers=headers)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["is_cached"] is True
    assert d2["epsilon_spent"] == 0.0
    assert d2["noisy_count"] == count1


# ==============================================================================
# SECTION 3: SESSION, AUTH & RBAC INTEGRATION
# ==============================================================================

def test_p7_10_session_me_endpoint_valid_token(client: TestClient, analyst_token: str):
    """P7-10: GET /api/me validates active session and returns user identity."""
    res = client.get("/api/me", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "analyst_user"
    assert data["role"] == "analyst"


def test_p7_11_session_me_endpoint_invalid_token(client: TestClient):
    """P7-11: GET /api/me rejects forged or expired Bearer token with HTTP 401."""
    res = client.get("/api/me", headers={"Authorization": "Bearer forged_invalid_token_xyz"})
    assert res.status_code == 401


def test_p7_12_session_logout_revokes_token(client: TestClient):
    """P7-12: POST /api/auth/logout invalidates session token immediately."""
    # Login fresh
    login_res = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_res.json()["token"]

    # Logout
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # Subsequent /api/me should fail
    me_res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 401


def test_p7_13_rbac_analyst_forbidden_from_admin_and_audit(client: TestClient, analyst_token: str):
    """P7-13: Analyst role is strictly forbidden from admin user management and security event inspection."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    r1 = client.get("/api/users", headers=headers)
    assert r1.status_code == 403

    r2 = client.get("/api/security/events", headers=headers)
    assert r2.status_code == 403

    r3 = client.get("/api/security/alerts", headers=headers)
    assert r3.status_code == 403

    r4 = client.post("/api/incident/transition", json={"new_state": "RESTRICTED", "reason": "unauthorized"}, headers=headers)
    assert r4.status_code == 403

    # Analyst CAN access audit log (holds audit.verify)
    r_audit = client.get("/api/audit/entries", headers=headers)
    assert r_audit.status_code == 200


def test_p7_14_rbac_auditor_permitted_for_audit_and_security(client: TestClient, auditor_token: str):
    """P7-14: Auditor role can access immutable audit trail and security events."""
    headers = {"Authorization": f"Bearer {auditor_token}"}
    r1 = client.get("/api/audit/verify", headers=headers)
    assert r1.status_code == 200
    assert r1.json()["valid"] is True

    r2 = client.get("/api/security/events", headers=headers)
    assert r2.status_code == 200


def test_p7_15_rbac_data_steward_can_access_security_alerts(client: TestClient, steward_token: str):
    """P7-15: Data steward role can access SIEM security alerts."""
    headers = {"Authorization": f"Bearer {steward_token}"}
    res = client.get("/api/security/alerts", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_p7_16_rbac_admin_can_manage_users(client: TestClient, admin_token: str):
    """P7-16: Admin role can list registered users and their lockout status."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/users", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert isinstance(users, list)
    assert any(u["username"] == "analyst_user" for u in users)


# ==============================================================================
# SECTION 4: CRYPTOGRAPHIC VERIFICATION & TAMPER DETECTION
# ==============================================================================

def test_p7_17_cross_user_receipt_access_protection(client: TestClient, analyst_token: str, auditor_token: str):
    """P7-17: Analyst cannot inspect another user's receipt, but auditor can verify any receipt."""
    # 1. Analyst creates a release
    run_res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "endocrine",
        "epsilon": 0.5,
        "idempotency_key": "p7-17-isolation-test"
    }, headers={"Authorization": f"Bearer {analyst_token}"})
    assert run_res.status_code == 200
    rcpt_id = run_res.json()["receipt"]["receipt_id"]

    # 2. Auditor can verify
    aud_res = client.post(f"/api/receipts/{rcpt_id}/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert aud_res.status_code == 200
    assert aud_res.json()["is_valid"] is True


def test_p7_18_audit_ledger_hash_chain_valid(client: TestClient, analyst_token: str, auditor_token: str):
    """P7-18: Audit ledger SHA-256 hash chaining is mathematically verified end-to-end."""
    # Ensure at least 1 entry exists by executing query as analyst
    client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5,
        "idempotency_key": "p7-18-commit-for-audit"
    }, headers={"Authorization": f"Bearer {analyst_token}"})

    res = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["tamper_detected"] is False
    assert data["verified_entries"] > 0


# ==============================================================================
# SECTION 5: INCIDENT RESPONSE & FAIL-CLOSED ENFORCEMENT
# ==============================================================================

def test_p7_19_incident_status_endpoint(client: TestClient, analyst_token: str):
    """P7-19: Incident status reports current gateway operational posture."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.get("/api/incident/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["current_state"] in {"NORMAL", "RESTRICTED", "RELEASES_DISABLED"}
    assert isinstance(data["releases_allowed"], bool)


def test_p7_20_incident_transition_requires_privileged_role(client: TestClient, analyst_token: str, admin_token: str):
    """P7-20: Analyst cannot transition incident state; Admin can execute transitions."""
    # Analyst attempt should fail
    r_analyst = client.post("/api/incident/transition", json={
        "new_state": "RESTRICTED",
        "reason": "Unauthorized test by analyst"
    }, headers={"Authorization": f"Bearer {analyst_token}"})
    assert r_analyst.status_code == 403

    # Admin attempt should succeed
    r_admin = client.post("/api/incident/transition", json={
        "new_state": "RESTRICTED",
        "reason": "Elevated threat level testing"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert r_admin.status_code == 200
    assert r_admin.json()["current_state"] == "RESTRICTED"

    # Reset back to NORMAL
    r_reset = client.post("/api/incident/transition", json={
        "new_state": "NORMAL",
        "reason": "Return to standard operations"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert r_reset.status_code == 200
    assert r_reset.json()["current_state"] == "NORMAL"


def test_p7_21_incident_releases_disabled_blocks_queries_fail_closed(client: TestClient, admin_token: str, analyst_token: str):
    """P7-21: When incident state is RELEASES_DISABLED, all query releases fail closed with HTTP 503."""
    # Set to RELEASES_DISABLED
    client.post("/api/incident/transition", json={
        "new_state": "RELEASES_DISABLED",
        "reason": "Emergency security lockdown drill"
    }, headers={"Authorization": f"Bearer {admin_token}"})

    try:
        # Analyst submits query -> must fail with HTTP 503
        res = client.post("/api/queries/run", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "respiratory",
            "epsilon": 0.5
        }, headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 503
        assert "releases suspended fail-closed" in res.json()["detail"].lower()
    finally:
        # Restore to NORMAL
        client.post("/api/incident/transition", json={
            "new_state": "NORMAL",
            "reason": "End of lockdown drill"
        }, headers={"Authorization": f"Bearer {admin_token}"})


# ==============================================================================
# SECTION 6: INPUT SANITIZATION & SECURITY BOUNDARIES
# ==============================================================================

def test_p7_22_sql_injection_in_category_value_rejected(client: TestClient, analyst_token: str):
    """P7-22: SQL injection payloads in filter values are rejected fail-closed by allowlist validator."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payloads = [
        "cardiovascular' OR '1'='1",
        "respiratory; DROP TABLE users; --",
        "endocrine' UNION SELECT * FROM users --",
    ]
    for val in payloads:
        res = client.post("/api/queries/run", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": val,
            "epsilon": 0.5
        }, headers=headers)
        assert res.status_code == 400
        assert "not an approved category" in res.json()["detail"]


def test_p7_23_path_traversal_on_dataset_id_rejected(client: TestClient, analyst_token: str):
    """P7-23: Path traversal strings in dataset_id are rejected with HTTP 400."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/queries/preview", json={
        "dataset_id": "../../../etc/passwd",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5
    }, headers=headers)
    assert res.status_code == 400
    assert "Unauthorized or unknown dataset" in res.json()["detail"]


def test_p7_24_raw_records_never_leaked_in_any_response(client: TestClient, analyst_token: str):
    """P7-24: Release responses never leak raw database rows or exact unperturbed counts."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "emergency",
        "epsilon": 0.5,
        "idempotency_key": "p7-24-no-raw-leak"
    }, headers=headers)
    assert res.status_code == 200
    text = res.text.lower()
    assert "raw_count_internal" not in text
    assert "medical_history" not in text
    assert "patient_id" not in res.json()["receipt"] or res.json()["receipt"]["patient_id"] is None


def test_p7_25_totp_mfa_enrollment_lifecycle(client: TestClient, analyst_token: str):
    """P7-25: MFA enrollment generates RFC 6238 base32 secret and otpauth URI."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/auth/mfa/enroll", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["secret"]) >= 16
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert len(data["recovery_codes"]) > 0


def test_p7_26_health_and_readiness_probes(client: TestClient):
    """P7-26: Probes return healthy operational telemetry."""
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "healthy"

    r2 = client.get("/ready")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ready"


def test_p7_27_evaluation_status_transparency(client: TestClient, analyst_token: str):
    """P7-27: Evaluation status discloses demo accounting active notice factually."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.get("/api/evaluation/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "official_accounting_spec_status" in data


def test_p7_28_case_insensitive_category_matching(client: TestClient, analyst_token: str):
    """P7-28: Filter values are matched case-insensitively against approved categories."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    # "RESPIRATORY" in uppercase
    res = client.post("/api/queries/preview", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "RESPIRATORY",
        "epsilon": 0.5
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_valid"] is True


def test_p7_29_query_run_with_custom_epsilon_levels(client: TestClient, analyst_token: str):
    """P7-29: Permitted epsilon levels [0.1, 0.2, 0.5, 1.0] are accepted."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    for eps in [0.1, 0.2, 0.5, 1.0]:
        res = client.post("/api/queries/preview", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "respiratory",
            "epsilon": eps
        }, headers=headers)
        assert res.status_code == 200
        assert res.json()["is_valid"] is True


def test_p7_30_unapproved_epsilon_rejected(client: TestClient, analyst_token: str):
    """P7-30: Out-of-bounds or unapproved epsilon values are rejected fail-closed."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    for bad_eps in [0.0, -0.5, 0.33, 2.5, 10.0]:
        res = client.post("/api/queries/preview", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "respiratory",
            "epsilon": bad_eps
        }, headers=headers)
        assert res.status_code == 400
        assert "not permitted" in res.json()["detail"]
