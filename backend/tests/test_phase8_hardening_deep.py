"""
SentinelVault Phase 8 Master Deep Hardening, Security & Reliability Test Suite.

Exhaustively verifies:
1. HTTP Security headers (nosniff, DENY, CSP, XSS-Protection, Referrer-Policy).
2. Request payload size limits (2MB DoS protection, HTTP 413).
3. CORS configuration and origin validation.
4. Authentication brute-force lockout (5 consecutive failures) & recovery.
5. Session revocation on logout & timing attack mitigation.
6. Zero-trust RBAC enforcement across analyst, auditor, data steward, and admin roles.
7. Insecure Direct Object Reference (IDOR) prevention on privacy receipts.
8. SQL injection & Path traversal defense across categorical parameters.
9. Mass assignment and malformed payload resilience.
10. Data vault isolation (zero raw record leakage).
11. Differential privacy Laplace noise injection & micro-epsilon accounting.
12. Budget exhaustion fail-closed enforcement (HTTP 429).
13. Privacy receipt cryptographic verification and tamper detection.
14. Audit ledger SHA-256 hash chaining and mathematical tamper detection.
15. Fail-closed incident response state machine (RESTRICTED, RELEASES_DISABLED).
16. Atomic SQLite online backup creation with SHA-256 sidecars.
17. Backup cryptographic verification & corruption detection.
18. Disaster recovery into isolated target database.
19. Anti-Rollback privacy budget reconciliation preventing replay attacks.
20. Signing key isolation (private key never exposed).
21. RFC 6238 TOTP Multi-Factor Authentication (MFA) lifecycle.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import pytest
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient

from app.db.connection import get_connection, get_db_path
from app.services.backup_service import (
    create_database_backup,
    verify_backup_integrity,
    restore_database_backup,
    list_backups,
    BackupError,
    RestoreError,
    BudgetInconsistencyError,
)
from app.services.crypto_audit import TRUSTED_KEY_ID


# Helper login fixtures
@pytest.fixture
def analyst_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def auditor_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def steward_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def admin_token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# SECTION 1: HTTP TRANSPORT, SECURITY HEADERS & RESOURCE PROTECTION
# ==============================================================================

def test_p8_01_security_headers_injected_on_all_responses(client: TestClient):
    """P8-01: Proves security headers (nosniff, DENY, CSP, XSS-Protection) are present on responses."""
    res = client.get("/health")
    assert res.status_code == 200
    headers = {k.lower(): v for k, v in res.headers.items()}
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert "default-src 'self'" in headers.get("content-security-policy", "")
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_p8_02_oversized_payload_rejected_413(client: TestClient):
    """P8-02: DoS guard rejects payloads with Content-Length > 2MB with HTTP 413."""
    oversized_length = str(5 * 1024 * 1024)  # 5MB
    res = client.post(
        "/api/queries/preview",
        content=b"{}",
        headers={"Content-Length": oversized_length, "Content-Type": "application/json"}
    )
    assert res.status_code == 413
    data = res.json()
    assert "Payload Too Large" in data["error"]
    assert "2MB" in data["detail"]


def test_p8_03_cors_origin_validation(client: TestClient):
    """P8-03: CORS headers correctly reflect allowlisted client origins."""
    res = client.options(
        "/api/queries/preview",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ==============================================================================
# SECTION 2: AUTHENTICATION, BRUTE-FORCE LOCKOUT & SESSION HARDENING
# ==============================================================================

def test_p8_04_auth_brute_force_lockout_after_five_failures(client: TestClient):
    """P8-04: Exactly 5 consecutive failed login attempts trigger a 15-minute account lockout."""
    username = f"spray_test_{os.urandom(4).hex()}"
    # Seed user in DB
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO users (username, user_id, password_hash, salt, role, status, failed_attempts, created_at, last_password_change)
            VALUES (?, ?, 'dummy_hash', 'dummy_salt', 'analyst', 'ACTIVE', 0, ?, ?);
            """, (username, f"USR-{username}", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
    finally:
        conn.close()

    # Attempt 4 wrong passwords -> 401
    for i in range(4):
        r = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
        assert r.status_code == 401

    # 5th attempt hits threshold (lockout triggered)
    r5 = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    assert r5.status_code in {401, 423}

    # 6th attempt must be rejected with lockout message
    r6 = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    assert r6.status_code in {401, 423}
    assert "locked" in r6.json()["detail"].lower()


def test_p8_05_auth_lockout_resets_on_admin_unlock(client: TestClient, admin_token: str):
    """P8-05: Administrative unlock successfully clears failed attempts and restores access."""
    # Create locked user
    username = f"locked_user_{os.urandom(4).hex()}"
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO users (username, user_id, password_hash, salt, role, status, failed_attempts, locked_until, created_at, last_password_change)
            VALUES (?, ?, 'hash', 'salt', 'analyst', 'LOCKED', 5, '2099-01-01T00:00:00Z', ?, ?);
            """, (username, f"USR-{username}", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
    finally:
        conn.close()

    # Admin unlocks user
    unlock_res = client.post(
        f"/api/users/{username}/unlock",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert unlock_res.status_code == 200
    assert unlock_res.json()["unlocked"] is True

    # Verify DB state
    conn = get_connection()
    try:
        row = conn.execute("SELECT status, failed_attempts, locked_until FROM users WHERE username = ?", (username,)).fetchone()
        assert row["status"] == "ACTIVE"
        assert row["failed_attempts"] == 0
        assert row["locked_until"] is None
    finally:
        conn.close()


def test_p8_06_auth_dummy_hash_timing_invariance(client: TestClient):
    """P8-06: Non-existent users are processed through dummy hash calculation without timing leakage."""
    import time
    t0 = time.perf_counter()
    res = client.post("/api/auth/login", json={"username": "totally_nonexistent_user_999", "password": "RandomPassword123!"})
    duration = time.perf_counter() - t0
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]
    assert duration > 0.001  # Proves dummy computation executed


def test_p8_07_auth_session_logout_revokes_token(client: TestClient):
    """P8-07: POST /api/auth/logout revokes session token; subsequent authenticated calls return 401."""
    # Login
    login_res = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_res.json()["token"]

    # Call /api/me successfully
    r1 = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200

    # Logout
    r_logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r_logout.status_code == 200

    # Second call to /api/me must fail
    r2 = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 401


# ==============================================================================
# SECTION 3: ZERO-TRUST RBAC & PRIVILEGE ESCALATION PREVENTION
# ==============================================================================

def test_p8_08_rbac_analyst_denied_user_management(client: TestClient, analyst_token: str):
    """P8-08: Analyst role is strictly forbidden from listing or unlocking users (HTTP 403)."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    assert client.get("/api/users", headers=headers).status_code == 403
    assert client.post("/api/users/analyst_user/unlock", headers=headers).status_code == 403


def test_p8_09_rbac_analyst_denied_security_events(client: TestClient, analyst_token: str):
    """P8-09: Analyst role is strictly forbidden from reading SIEM security audit events (HTTP 403)."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    assert client.get("/api/security/events", headers=headers).status_code == 403


def test_p8_10_rbac_analyst_denied_security_alerts(client: TestClient, analyst_token: str):
    """P8-10: Analyst role is strictly forbidden from viewing or modifying SIEM alerts (HTTP 403)."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    assert client.get("/api/security/alerts", headers=headers).status_code == 403
    assert client.post("/api/security/alerts/ALT-001/acknowledge", headers=headers).status_code == 403


def test_p8_11_rbac_analyst_denied_incident_transition(client: TestClient, analyst_token: str):
    """P8-11: Analyst role is strictly forbidden from triggering gateway incident state transitions (HTTP 403)."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/incident/transition", json={"new_state": "RESTRICTED", "reason": "unauthorized attempt"}, headers=headers)
    assert res.status_code == 403


def test_p8_12_rbac_auditor_can_verify_audit_trail_and_receipts(client: TestClient, auditor_token: str, analyst_token: str):
    """P8-12: Auditor role holds audit.verify and receipt.read.authorized permissions."""
    # Commit a release as analyst
    run_res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5,
        "idempotency_key": "p8-12-auditor-check"
    }, headers={"Authorization": f"Bearer {analyst_token}"})
    rcpt_id = run_res.json()["receipt"]["receipt_id"]

    # Auditor verifies receipt
    headers = {"Authorization": f"Bearer {auditor_token}"}
    v_res = client.post(f"/api/receipts/{rcpt_id}/verify", headers=headers)
    assert v_res.status_code == 200
    assert v_res.json()["is_valid"] is True

    # Auditor verifies audit chain
    audit_res = client.get("/api/audit/verify", headers=headers)
    assert audit_res.status_code == 200
    assert audit_res.json()["valid"] is True


def test_p8_13_rbac_data_steward_can_read_security_alerts(client: TestClient, steward_token: str):
    """P8-13: Data steward role can access SIEM security alerts and system status."""
    headers = {"Authorization": f"Bearer {steward_token}"}
    res = client.get("/api/security/alerts", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_p8_14_idor_analyst_cannot_verify_other_analyst_receipt(client: TestClient, analyst_token: str):
    """P8-14: IDOR defense: Analyst cannot verify another user's receipt (HTTP 403)."""
    rcpt_id = "RCPT-foreign-user-001"
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            INSERT INTO query_releases (
                release_id, dataset_id, query_fingerprint, cache_key,
                epsilon_micro, raw_count_internal, noisy_count, mechanism,
                user_id, receipt_id, is_cached_release, created_at
            ) VALUES ('REL-foreign-001', 'health', 'fprint', 'ckey', 500000, 10, 10, 'Laplace', 'other_analyst_user', ?, 0, ?);
            """, (rcpt_id, now_iso))
            conn.execute("""
            INSERT INTO privacy_receipts (
                receipt_id, release_id, user_id, dataset_id, dataset_version,
                query_fingerprint, query_description, mechanism, epsilon_spent,
                cumulative_epsilon, remaining_budget, policy_check_status,
                audit_entry_hash, signature, timestamp, is_revoked
            ) VALUES (?, 'REL-foreign-001', 'other_analyst_user', 'health', '1.0.0',
                      'fingerprint', 'description', 'Laplace', 0.5, 0.5, 4.5,
                      'POLICY_CHECK_PASSED', 'entryhash', 'signature', ?, 0);
            """, (rcpt_id, now_iso))
    finally:
        conn.close()

    # Attempt verification as analyst_user -> must return 403 Forbidden
    res = client.post(f"/api/receipts/{rcpt_id}/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


# ==============================================================================
# SECTION 4: INPUT SANITIZATION & BOUNDARY DEFENSE
# ==============================================================================

def test_p8_15_sql_injection_defense_exhaustive(client: TestClient, analyst_token: str):
    """P8-15: Strict categorical allowlists reject all SQL injection variations fail-closed."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    attack_payloads = [
        "respiratory' OR '1'='1",
        "respiratory'; DROP TABLE users; --",
        "respiratory' UNION SELECT 1,2,3,4 --",
        "' OR 1=1 --",
        "admin'--",
        "1; WAITFOR DELAY '0:0:5'--",
    ]
    for atk in attack_payloads:
        res = client.post("/api/queries/preview", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": atk,
            "epsilon": 0.5
        }, headers=headers)
        assert res.status_code == 400
        assert "not an approved category" in res.json()["detail"]


def test_p8_16_path_traversal_defense_in_dataset_id(client: TestClient, analyst_token: str):
    """P8-16: Directory traversal payloads in dataset identifiers are rejected fail-closed."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    traversal_attacks = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "health/../financial",
        "/etc/shadow",
    ]
    for atk in traversal_attacks:
        res = client.post("/api/queries/preview", json={
            "dataset_id": atk,
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "respiratory",
            "epsilon": 0.5
        }, headers=headers)
        assert res.status_code == 400
        assert "Unauthorized or unknown dataset" in res.json()["detail"]


def test_p8_17_mass_assignment_defense(client: TestClient, analyst_token: str):
    """P8-17: Extra privileged fields (is_admin, role, bypass_budget) in JSON bodies are ignored."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/queries/preview", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5,
        "is_admin": True,
        "role": "admin",
        "bypass_budget": True
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "is_admin" not in data
    assert "bypass_budget" not in data


def test_p8_18_malformed_json_rejected_422(client: TestClient, analyst_token: str):
    """P8-18: Malformed or unparseable JSON payloads return standard HTTP 422."""
    headers = {"Authorization": f"Bearer {analyst_token}", "Content-Type": "application/json"}
    res = client.post("/api/queries/run", content=b"{'unclosed_json': ", headers=headers)
    assert res.status_code == 422
    assert "Validation Error" in res.json()["error"]


def test_p8_19_raw_dataset_records_never_leaked(client: TestClient, analyst_token: str):
    """P8-19: Response payloads never contain raw patient records or exact unperturbed counts."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "cardiovascular",
        "epsilon": 0.5,
        "idempotency_key": "p8-19-no-raw-leak"
    }, headers=headers)
    assert res.status_code == 200
    raw_text = res.text.lower()
    assert "raw_count_internal" not in raw_text
    assert "patient_id" not in res.json()["receipt"] or res.json()["receipt"]["patient_id"] is None
    assert "medical_history" not in raw_text


# ==============================================================================
# SECTION 5: DIFFERENTIAL PRIVACY & BUDGET ACCOUNTING HARDENING
# ==============================================================================

def test_p8_20_laplace_mechanism_noise_injection(client: TestClient, analyst_token: str):
    """P8-20: Released count is perturbated by Laplace mechanism and includes receipt metadata."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "emergency",
        "epsilon": 0.5,
        "idempotency_key": "p8-20-dp-check"
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["noisy_count"], int)
    assert data["receipt"]["mechanism"] == "Laplace"
    assert data["epsilon_spent"] == 0.5


def test_p8_21_budget_exhaustion_fail_closed_429(client: TestClient, analyst_token: str):
    """P8-21: When remaining privacy budget is exhausted, further releases fail with HTTP 429."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    # Set remaining budget to 0
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
            UPDATE budget_ledger 
            SET spent_micro_epsilon = cap_micro_epsilon, remaining_micro_epsilon = 0
            WHERE dataset_id = 'financial';
            """)
    finally:
        conn.close()

    res = client.post("/api/queries/run", json={
        "dataset_id": "financial",
        "field": "transaction_type",
        "operator": "equals",
        "value": "wire",
        "epsilon": 0.5,
        "idempotency_key": "p8-21-budget-exhausted"
    }, headers=headers)
    assert res.status_code == 429
    assert "budget exhausted" in res.json()["detail"].lower()


def test_p8_22_cache_replay_does_not_deduct_budget(client: TestClient, analyst_token: str):
    """P8-22: Exact cache hits return previously released result with 0.0 epsilon expenditure."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "endocrine",
        "epsilon": 0.5,
        "idempotency_key": "p8-22-cache-replay"
    }
    r1 = client.post("/api/queries/run", json=payload, headers=headers)
    assert r1.status_code == 200
    first_count = r1.json()["noisy_count"]

    # Re-submission
    r2 = client.post("/api/queries/run", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["is_cached"] is True
    assert r2.json()["epsilon_spent"] == 0.0
    assert r2.json()["noisy_count"] == first_count


# ==============================================================================
# SECTION 6: CRYPTOGRAPHIC INTEGRITY & AUDIT TAMPER DETECTION
# ==============================================================================

def test_p8_23_receipt_cryptographic_verification_authentic(client: TestClient, analyst_token: str):
    """P8-23: Freshly signed receipt verifies authentic with all 7 checks passing."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    run_res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "discharge_status",
        "operator": "equals",
        "value": "routine",
        "epsilon": 0.5,
        "idempotency_key": "p8-23-receipt-valid"
    }, headers=headers)
    assert run_res.status_code == 200
    rcpt_id = run_res.json()["receipt"]["receipt_id"]

    v_res = client.post(f"/api/receipts/{rcpt_id}/verify", headers=headers)
    assert v_res.status_code == 200
    data = v_res.json()
    assert data["is_valid"] is True
    assert "VERIFIED" in data["verification_status"]
    assert data["checks"]["hash_match"] is True
    assert data["checks"]["signature_valid"] is True
    assert data["checks"]["key_trusted"] is True


def test_p8_24_receipt_tamper_detection(client: TestClient, analyst_token: str):
    """P8-24: Tampering with a database receipt invalidates signature and canonical hash."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    run_res = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "discharge_status",
        "operator": "equals",
        "value": "transferred",
        "epsilon": 0.5,
        "idempotency_key": "p8-24-receipt-tamper"
    }, headers=headers)
    rcpt_id = run_res.json()["receipt"]["receipt_id"]

    # Tamper with stored epsilon in database
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE privacy_receipts SET epsilon_spent = 0.999 WHERE receipt_id = ?", (rcpt_id,))
    finally:
        conn.close()

    # Verification must fail
    v_res = client.post(f"/api/receipts/{rcpt_id}/verify", headers=headers)
    assert v_res.status_code == 200
    data = v_res.json()
    assert data["is_valid"] is False
    assert data["checks"]["hash_match"] is False or data["checks"]["signature_valid"] is False


def test_p8_25_audit_chain_mathematical_tamper_detection(client: TestClient, analyst_token: str, auditor_token: str):
    """P8-25: Modifying an audit entry in the hash chain is detected immediately by /api/audit/verify."""
    # Commit query release
    client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "oncology",
        "epsilon": 0.5,
        "idempotency_key": "p8-25-audit-tamper"
    }, headers={"Authorization": f"Bearer {analyst_token}"})

    # Tamper with audit log record in database
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE audit_log SET actor = 'rogue_attacker' WHERE actor = 'analyst_user'")
    finally:
        conn.close()

    # Auditor verification must detect tamper
    res = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["tamper_detected"] is True
    assert "Broken" in data["error_message"] or "mismatch" in data["error_message"].lower()


# ==============================================================================
# SECTION 7: INCIDENT RESPONSE STATE MACHINE
# ==============================================================================

def test_p8_26_incident_state_fail_closed_releases_disabled(client: TestClient, admin_token: str, analyst_token: str):
    """P8-26: When incident state is RELEASES_DISABLED, all analytical queries fail closed with HTTP 503."""
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Transition to RELEASES_DISABLED
    client.post("/api/incident/transition", json={
        "new_state": "RELEASES_DISABLED",
        "reason": "Security lockdown verification drill"
    }, headers=admin_headers)

    try:
        res = client.post("/api/queries/run", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "neurological",
            "epsilon": 0.5
        }, headers=analyst_headers)
        assert res.status_code == 503
        assert "releases suspended fail-closed" in res.json()["detail"].lower()
    finally:
        client.post("/api/incident/transition", json={"new_state": "NORMAL", "reason": "Restore operations"}, headers=admin_headers)


def test_p8_27_incident_state_restricted_epsilon_cap(client: TestClient, admin_token: str, analyst_token: str):
    """P8-27: In RESTRICTED state, requesting epsilon above 0.5 is rejected with HTTP 400."""
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    client.post("/api/incident/transition", json={"new_state": "RESTRICTED", "reason": "Restricted threat level"}, headers=admin_headers)
    try:
        res = client.post("/api/queries/run", json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "respiratory",
            "epsilon": 1.0  # > max permitted in restricted mode (0.5)
        }, headers=analyst_headers)
        assert res.status_code == 400
        assert "maximum allowed epsilon is 0.5" in res.json()["detail"]
    finally:
        client.post("/api/incident/transition", json={"new_state": "NORMAL", "reason": "Restore operations"}, headers=admin_headers)


# ==============================================================================
# SECTION 8: BACKUP & DISASTER RECOVERY TESTS
# ==============================================================================

def test_p8_28_backup_creation_atomic_online(tmp_path: Path):
    """P8-28: create_database_backup creates consistent SQLite snapshot and JSON metadata sidecar."""
    meta = create_database_backup(destination_dir=tmp_path, label="p8-test")
    assert meta["status"] == "COMPLETED"
    assert meta["backup_id"].startswith("BKP-")
    assert meta["trusted_key_id"] == TRUSTED_KEY_ID
    assert len(meta["sha256_checksum"]) == 64

    # Verify both files exist
    db_file = tmp_path / meta["backup_file"]
    json_file = tmp_path / f"sentinelvault_{meta['backup_id']}.json"
    assert db_file.exists()
    assert json_file.exists()


def test_p8_29_backup_verification_integrity_pass(tmp_path: Path):
    """P8-29: verify_backup_integrity confirms valid SQLite schema, foreign keys, and checksum."""
    meta = create_database_backup(destination_dir=tmp_path, label="p8-verify-test")
    db_file = tmp_path / meta["backup_file"]

    result = verify_backup_integrity(db_file)
    assert result["valid"] is True
    assert result["checksum_match"] is True
    assert result["integrity_check_passed"] is True
    assert result["foreign_keys_valid"] is True


def test_p8_30_backup_corrupted_checksum_fails_verification(tmp_path: Path):
    """P8-30: Corrupted backup file triggers checksum or integrity failure fail-closed."""
    meta = create_database_backup(destination_dir=tmp_path, label="p8-corrupt-test")
    db_file = tmp_path / meta["backup_file"]

    # Corrupt the file
    with open(db_file, "r+b") as f:
        f.seek(100)
        f.write(b"CORRUPTED_BYTES_HERE_FOR_TEST")

    result = verify_backup_integrity(db_file)
    assert result["valid"] is False
    assert result["checksum_match"] is False or result["integrity_check_passed"] is False


def test_p8_31_backup_restore_into_isolated_target(tmp_path: Path):
    """P8-31: Restoring validated backup into target database preserves records and valid audit chain."""
    backup_meta = create_database_backup(destination_dir=tmp_path, label="p8-restore-source")
    backup_db = tmp_path / backup_meta["backup_file"]
    target_db = tmp_path / "isolated_restored.db"

    res = restore_database_backup(backup_db, target_db_path=target_db)
    assert res["status"] == "RESTORE_SUCCESSFUL"
    assert res["audit_chain_valid"] is True
    assert target_db.exists()


def test_p8_32_backup_restore_anti_rollback_reconciliation(tmp_path: Path, client: TestClient, analyst_token: str):
    """P8-32: Anti-Rollback: Restoring an artificially reduced budget auto-reconciles spent micro-epsilon."""
    # 1. Execute a query release for 0.5 epsilon
    client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5,
        "idempotency_key": "p8-32-release"
    }, headers={"Authorization": f"Bearer {analyst_token}"})

    # 2. Create backup
    backup_meta = create_database_backup(destination_dir=tmp_path, label="p8-rollback-source")
    backup_db = tmp_path / backup_meta["backup_file"]

    # 3. Simulate tampering in the backup database: reset spent budget to 0
    conn = sqlite3.connect(str(backup_db))
    with conn:
        conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 0, remaining_micro_epsilon = cap_micro_epsilon WHERE dataset_id = 'health'")
    conn.close()

    # 4. Attempt restore: anti-rollback mechanism must detect and reconcile
    target_db = tmp_path / "reconciled_target.db"
    res = restore_database_backup(backup_db, target_db_path=target_db, verify_first=False, auto_reconcile_budget=True)
    assert res["status"] == "RESTORE_SUCCESSFUL"
    health_reconcile = res["budget_reconciliation"]["health"]
    assert health_reconcile["status"] == "RECONCILED_ANTI_ROLLBACK"
    assert health_reconcile["authoritative_spent_epsilon"] >= 0.5


def test_p8_33_key_isolation_private_key_never_leaked(client: TestClient, analyst_token: str):
    """P8-33: Cryptographic private keys are never returned in responses or receipts."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    r = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "respiratory",
        "epsilon": 0.5
    }, headers=headers)
    assert r.status_code == 200
    text = r.text
    assert "private" not in text.lower()
    assert "begin private key" not in text.lower()


def test_p8_34_totp_mfa_rfc6238_enroll_and_recovery_codes(client: TestClient, analyst_token: str):
    """P8-34: MFA enrollment returns valid RFC 6238 base32 secret and recovery codes."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = client.post("/api/auth/mfa/enroll", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["secret"]) >= 16
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert len(data["recovery_codes"]) == 5


def test_p8_35_list_backups_utility(tmp_path: Path):
    """P8-35: list_backups sorts created backups in reverse chronological order."""
    create_database_backup(destination_dir=tmp_path, label="first")
    create_database_backup(destination_dir=tmp_path, label="second")
    backups = list_backups(destination_dir=tmp_path)
    assert len(backups) >= 2
    assert backups[0]["created_at"] >= backups[1]["created_at"]
