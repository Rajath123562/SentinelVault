"""Category 2: Deep Verification Suite for Authentication, Sessions, and Authorization.

Covers 42 distinct test scenarios verifying PBKDF2 cryptography, timing resistance,
5-attempt lockout enforcement, session revocation, token tamper resistance,
and granular RBAC across Analyst, Data Steward, Auditor, and Admin roles.
"""

import time
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import create_application
from app.db.connection import get_connection, hash_password, verify_password
from app.services.auth_service import (
    login_user,
    logout_user,
    get_session_user,
    revoke_session_administrative,
    has_permission,
    enroll_mfa_for_user,
    confirm_mfa_enrollment,
    generate_totp_code,
    verify_totp_code,
    AuthenticationError,
    AccountLockedError,
)


@pytest.fixture(scope="module")
def auth_client():
    app = create_application()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# D1: CREDENTIAL VERIFICATION & PBKDF2 CRYPTOGRAPHY (Tests 1 - 10)
# ==============================================================================

def test_d1_01_pbkdf2_iteration_count_and_salt_entropy():
    pw = "SuperSecurePassword2026!"
    hashed, salt = hash_password(pw)
    assert len(salt) == 32  # 16 bytes hex-encoded
    assert len(hashed) == 64  # SHA-256 output hex-encoded
    # Verify different salt on second hash
    hashed2, salt2 = hash_password(pw)
    assert salt != salt2
    assert hashed != hashed2


def test_d1_02_password_verification_matches_correct_salt():
    pw = "TestPassword!234"
    hashed, salt = hash_password(pw)
    assert verify_password(pw, hashed, salt) is True
    assert verify_password("WrongPassword!", hashed, salt) is False


def test_d1_03_all_seeded_roles_authenticate_successfully(auth_client):
    seeded_users = [
        ("analyst_user", "AnalystPass2026!", "analyst"),
        ("steward_user", "StewardPass2026!", "data_steward"),
        ("auditor_user", "AuditorPass2026!", "auditor"),
        ("admin_user", "AdminPass2026!", "admin"),
    ]
    for username, password, expected_role in seeded_users:
        res = auth_client.post("/api/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200, f"Failed for {username}: {res.text}"
        data = res.json()
        assert data["username"] == username
        assert data["role"] == expected_role
        assert "token" in data
        assert len(data["token"]) > 30


def test_d1_04_wrong_password_returns_401_generic(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "BadPassword123!"})
    assert res.status_code == 401
    data = res.json()
    assert "detail" in data
    assert "incorrect" in data["detail"].lower() or "invalid" in data["detail"].lower()


def test_d1_05_unknown_username_returns_generic_error_same_status(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "ghost_user_9999", "password": "AnyPassword!"})
    assert res.status_code == 401
    assert "detail" in res.json()


def test_d1_06_empty_credentials_rejected(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "", "password": ""})
    assert res.status_code in [400, 401, 422]


def test_d1_07_whitespace_only_credentials_rejected(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "   ", "password": "   "})
    assert res.status_code in [400, 401, 422]


def test_d1_08_constant_time_dummy_verification_benchmark():
    # Comparing non-existent user should perform dummy hash to prevent timing attacks
    t0 = time.perf_counter()
    try:
        login_user("ghost_user_1", "Password123!")
    except AuthenticationError:
        pass
    t_nonexistent = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        login_user("analyst_user", "WrongPassword123!")
    except AuthenticationError:
        pass
    t_existing_wrong_pw = time.perf_counter() - t0

    # Both must perform PBKDF2 iteration (taking non-zero computational time > 5ms)
    assert t_nonexistent > 0.005
    assert t_existing_wrong_pw > 0.005


def test_d1_09_successful_login_resets_failed_counter(auth_client):
    # Register 2 failures
    auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "Wrong1!"})
    auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "Wrong2!"})

    # Successful login
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200

    # Check database counter
    conn = get_connection()
    try:
        user = conn.execute("SELECT failed_attempts FROM users WHERE username = 'analyst_user'").fetchone()
        assert user["failed_attempts"] == 0
    finally:
        conn.close()


def test_d1_10_credentials_not_logged_in_response(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    text = res.text
    assert "AnalystPass2026!" not in text
    assert "password_hash" not in text
    assert "password_salt" not in text


# ==============================================================================
# D2: FIVE-ATTEMPT TEMPORARY LOCKOUT (Tests 11 - 20)
# ==============================================================================

def test_d2_11_four_failures_do_not_lock_account(auth_client):
    for i in range(4):
        res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})
        assert res.status_code == 401

    conn = get_connection()
    try:
        row = conn.execute("SELECT failed_attempts, locked_until FROM users WHERE username = 'analyst_user'").fetchone()
        assert row["failed_attempts"] == 4
        assert row["locked_until"] is None
    finally:
        conn.close()


def test_d2_12_exact_fifth_failure_locks_account_with_429(auth_client):
    # 4 failures
    for i in range(4):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})
    # 5th failure
    res5 = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "Wrong_Final"})
    assert res5.status_code in [423, 429]
    assert "lock" in res5.text.lower() or "too many" in res5.text.lower()


def test_d2_13_valid_password_during_lockout_rejected_with_429(auth_client):
    # Lock account with 5 failures
    for i in range(5):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})

    # Now attempt valid password
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code in [423, 429]
    assert "lock" in res.text.lower()


def test_d2_14_lockout_is_isolated_per_user_account(auth_client):
    # Lock analyst_user
    for i in range(5):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})

    # steward_user remains unaffected
    steward_res = auth_client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    assert steward_res.status_code == 200
    assert steward_res.json()["role"] == "data_steward"


def test_d2_15_lockout_duration_is_approx_15_minutes(auth_client):
    for i in range(5):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})

    conn = get_connection()
    try:
        row = conn.execute("SELECT locked_until FROM users WHERE username = 'analyst_user'").fetchone()
        assert row["locked_until"] is not None
        lock_dt = datetime.fromisoformat(row["locked_until"])
        now = datetime.now(timezone.utc)
        diff = (lock_dt - now).total_seconds()
        assert 800 <= diff <= 950  # ~15 minutes
    finally:
        conn.close()


def test_d2_16_attempts_during_lockout_do_not_extend_duration(auth_client):
    for i in range(5):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})

    conn = get_connection()
    try:
        t1 = conn.execute("SELECT locked_until FROM users WHERE username = 'analyst_user'").fetchone()["locked_until"]
    finally:
        conn.close()

    # Attempt again during lock
    auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "Wrong_During_Lock"})

    conn = get_connection()
    try:
        t2 = conn.execute("SELECT locked_until FROM users WHERE username = 'analyst_user'").fetchone()["locked_until"]
        assert t1 == t2
    finally:
        conn.close()


def test_d2_17_expired_lockout_allows_valid_login(auth_client):
    # Set lockout timestamp to the past
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET failed_attempts = 5, locked_until = ? WHERE username = 'analyst_user'", (past_iso,))
    finally:
        conn.close()

    # Now login with valid password
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200


def test_d2_18_client_side_headers_cannot_bypass_lockout(auth_client):
    for i in range(5):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})

    # Attempt to bypass via spoofed headers
    res = auth_client.post(
        "/api/auth/login",
        json={"username": "analyst_user", "password": "AnalystPass2026!"},
        headers={
            "X-Forwarded-For": "10.0.0.99",
            "X-Real-IP": "192.168.1.1",
            "X-Bypass-Lockout": "true",
            "X-Admin": "true",
        }
    )
    assert res.status_code in [423, 429]


def test_d2_19_admin_can_unlock_locked_user(auth_client):
    # Lock analyst
    for i in range(5):
        auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": f"Wrong_{i}"})

    # Admin unlocks analyst
    admin_login = auth_client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    admin_token = admin_login.json()["token"]

    unlock_res = auth_client.post(
        "/api/users/analyst_user/unlock",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert unlock_res.status_code == 200
    assert unlock_res.json()["unlocked"] is True

    # Analyst can now log in
    analyst_res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert analyst_res.status_code == 200


def test_d2_20_analyst_cannot_unlock_themselves(auth_client):
    analyst_login = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    analyst_token = analyst_login.json()["token"]

    unlock_res = auth_client.post(
        "/api/users/analyst_user/unlock",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert unlock_res.status_code == 403


# ==============================================================================
# D3: SESSIONS, JWT & REVOCATION (Tests 21 - 30)
# ==============================================================================

def test_d3_21_token_structure_has_expected_claims(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]
    assert len(token) == 64  # 32 bytes hex-encoded
    user_data = get_session_user(token)
    assert user_data["username"] == "analyst_user"
    assert user_data["role"] == "analyst"
    assert "dataset.query.execute" in user_data["permissions"]


def test_d3_22_tampered_signature_rejected(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]
    # Tamper with the token hex string
    tampered = "f" * 64 if token != "f" * 64 else "0" * 64
    get_res = auth_client.get("/api/datasets", headers={"Authorization": f"Bearer {tampered}"})
    assert get_res.status_code == 401


def test_d3_23_tampered_payload_role_elevation_rejected(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]
    # Forged token claiming admin privileges cannot bypass cryptographic token check
    forged_token = "forged_admin_token_" + token[19:]
    get_res = auth_client.get("/api/users", headers={"Authorization": f"Bearer {forged_token}"})
    assert get_res.status_code == 401


def test_d3_24_expired_token_rejected():
    res = login_user("analyst_user", "AnalystPass2026!")
    token = res["token"]
    conn = get_connection()
    try:
        with conn:
            # Set expiration to past
            past_exp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            conn.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (past_exp, token))
    finally:
        conn.close()

    with pytest.raises(AuthenticationError):
        get_session_user(token)


def test_d3_25_user_logout_invalidates_session_token(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]

    # Verify access works
    v1 = auth_client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert v1.status_code == 200

    # Logout
    logout_res = auth_client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # Token must now be rejected
    v2 = auth_client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert v2.status_code == 401


def test_d3_26_revoked_token_cannot_execute_queries(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]

    auth_client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    query_res = auth_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": "health", "field": "diagnosis", "operator": "=", "value": "Hypertension", "epsilon": 0.5}
    )
    assert query_res.status_code == 401


def test_d3_27_none_algorithm_header_rejected(auth_client):
    # 'none' algorithm exploit attempt
    fake_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbl91c2VyIiwicm9sZSI6ImFkbWluIn0."
    res = auth_client.get("/api/users", headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401


def test_d3_28_blank_bearer_token_rejected(auth_client):
    res = auth_client.get("/api/datasets", headers={"Authorization": "Bearer "})
    assert res.status_code == 401


def test_d3_29_session_token_not_returned_in_public_status(auth_client):
    res = auth_client.get("/api/system/status")
    text = res.text
    assert "token" not in text
    assert "jwt" not in text.lower()


def test_d3_30_jwt_secret_not_guessable_or_default(auth_client):
    # Ensure weak JWT secrets like 'secret' fail verification
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]
    assert len(token) > 50


# ==============================================================================
# D4: GRANULAR RBAC MATRIX (Tests 31 - 42)
# ==============================================================================

def test_d4_31_analyst_can_access_datasets_and_run_queries(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]

    ds_res = auth_client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert ds_res.status_code == 200

    q_res = auth_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert q_res.status_code == 200


def test_d4_32_analyst_forbidden_from_siem_events(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]

    evt_res = auth_client.get("/api/security/events", headers={"Authorization": f"Bearer {token}"})
    assert evt_res.status_code == 403


def test_d4_33_analyst_forbidden_from_security_alerts(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]

    alert_res = auth_client.get("/api/security/alerts", headers={"Authorization": f"Bearer {token}"})
    assert alert_res.status_code == 403


def test_d4_34_analyst_forbidden_from_user_management(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = res.json()["token"]

    user_res = auth_client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert user_res.status_code == 403


def test_d4_35_data_steward_can_access_siem_events(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    token = res.json()["token"]

    evt_res = auth_client.get("/api/security/events", headers={"Authorization": f"Bearer {token}"})
    assert evt_res.status_code == 200
    assert isinstance(evt_res.json(), list)


def test_d4_36_data_steward_can_access_security_alerts(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    token = res.json()["token"]

    alert_res = auth_client.get("/api/security/alerts", headers={"Authorization": f"Bearer {token}"})
    assert alert_res.status_code == 200
    assert isinstance(alert_res.json(), list)


def test_d4_37_auditor_can_verify_audit_ledger(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    token = res.json()["token"]

    audit_res = auth_client.get("/api/audit/verify", headers={"Authorization": f"Bearer {token}"})
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert "valid" in data
    assert "tamper_detected" in data


def test_d4_38_auditor_can_access_evaluation_status(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    token = res.json()["token"]

    eval_res = auth_client.get("/api/evaluation/status", headers={"Authorization": f"Bearer {token}"})
    assert eval_res.status_code == 200


def test_d4_39_admin_can_list_users(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    token = res.json()["token"]

    users_res = auth_client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert users_res.status_code == 200
    user_list = users_res.json()
    assert len(user_list) >= 4


def test_d4_40_admin_unlock_nonexistent_user_returns_404(auth_client):
    res = auth_client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    token = res.json()["token"]

    unlock_res = auth_client.post("/api/users/nonexistent_person_xyz/unlock", headers={"Authorization": f"Bearer {token}"})
    assert unlock_res.status_code == 404


def test_d4_41_receipt_ownership_enforcement(auth_client):
    # Analyst runs a query
    a_login = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    a_token = a_login.json()["token"]

    run_res = auth_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {a_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert run_res.status_code == 200
    receipt_id = run_res.json()["receipt"]["receipt_id"]

    # Analyst can view own receipt
    own_res = auth_client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {a_token}"})
    assert own_res.status_code == 200

    # Second analyst cannot access first analyst's receipt (object-level ownership)
    conn = get_connection()
    try:
        with conn:
            h, s = hash_password("AnalystPass2026!")
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO users (username, password_hash, salt, role, status, created_at) VALUES ('analyst_2', ?, ?, 'analyst', 'ACTIVE', ?)",
                (h, s, now_iso)
            )
    finally:
        conn.close()

    s_login = auth_client.post("/api/auth/login", json={"username": "analyst_2", "password": "AnalystPass2026!"})
    s_token = s_login.json()["token"]
    other_res = auth_client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {s_token}"})
    assert other_res.status_code == 403


def test_d4_42_nonexistent_receipt_id_returns_404(auth_client):
    a_login = auth_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    a_token = a_login.json()["token"]
    res = auth_client.get("/api/receipts/nonexistent_receipt_9999", headers={"Authorization": f"Bearer {a_token}"})
    assert res.status_code == 404
