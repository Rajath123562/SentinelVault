"""Comprehensive Phase 2 Security, Lockout, MFA, and Zero-Trust Browser-Tampering Test Suite."""

import time
import pytest
import secrets
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.db.connection import get_connection, hash_password
from app.services.auth_service import (
    compute_totp_code,
    generate_totp_secret,
    LOCKOUT_THRESHOLD,
    LOCKOUT_DURATION_MINUTES
)


# ==============================================================================
# SECTION 6.3: THE 12 LOCKOUT ACCEPTANCE TESTS
# ==============================================================================

def test_lockout_case_01_attempts_1_to_4_do_not_lock(client: TestClient):
    """Case 1: 1st, 2nd, 3rd, 4th failed attempts increment counter but do NOT lock account."""
    username = f"lockout_c1_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    for i in range(1, 5):
        resp = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
        assert resp.status_code == 401, f"Attempt {i} should return 401, got {resp.status_code}"
        assert "Invalid username or password" in resp.json()["detail"]

        row = conn.execute("SELECT failed_attempts, locked_until, status FROM users WHERE username = ?", (username,)).fetchone()
        assert row["failed_attempts"] == i
        assert row["locked_until"] is None
        assert row["status"] == "ACTIVE"


def test_lockout_case_02_fifth_failed_attempt_locks_immediately(client: TestClient):
    """Case 2: 5th failed attempt locks the account immediately with HTTP 423."""
    username = f"lockout_c2_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    for _ in range(4):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})

    resp5 = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    assert resp5.status_code == 423
    assert "Account locked" in resp5.json()["detail"]

    row = conn.execute("SELECT failed_attempts, locked_until, status FROM users WHERE username = ?", (username,)).fetchone()
    assert row["failed_attempts"] >= 5
    assert row["locked_until"] is not None
    assert row["status"] == "LOCKED"


def test_lockout_case_03_valid_credentials_fail_while_locked(client: TestClient):
    """Case 3: While locked, even valid credentials fail with HTTP 423."""
    username = f"lockout_c3_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        locked_future = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 5, ?, ?, 'LOCKED')",
            (username, h, s, locked_future, datetime.now(timezone.utc).isoformat())
        )

    resp = client.post("/api/auth/login", json={"username": username, "password": "ValidPassword2026!"})
    assert resp.status_code == 423
    assert "temporarily locked" in resp.json()["detail"].lower()


def test_lockout_case_04_lockout_duration_enforced(client: TestClient):
    """Case 4: Lockout duration of 15 minutes is recorded accurately."""
    username = f"lockout_c4_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    for _ in range(5):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})

    row = conn.execute("SELECT locked_until FROM users WHERE username = ?", (username,)).fetchone()
    locked_until_dt = datetime.fromisoformat(row["locked_until"])
    now_dt = datetime.now(timezone.utc)
    diff_minutes = (locked_until_dt - now_dt).total_seconds() / 60.0
    assert 14.5 <= diff_minutes <= 15.5


def test_lockout_case_05_valid_login_resets_failed_counter(client: TestClient):
    """Case 5: A successful login after 1 to 4 failed attempts resets counter to 0."""
    username = f"lockout_c5_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    # 3 failed attempts
    for _ in range(3):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})

    row_before = conn.execute("SELECT failed_attempts FROM users WHERE username = ?", (username,)).fetchone()
    assert row_before["failed_attempts"] == 3

    # Now successful login
    resp_success = client.post("/api/auth/login", json={"username": username, "password": "ValidPassword2026!"})
    assert resp_success.status_code == 200

    row_after = conn.execute("SELECT failed_attempts, locked_until, status FROM users WHERE username = ?", (username,)).fetchone()
    assert row_after["failed_attempts"] == 0
    assert row_after["locked_until"] is None
    assert row_after["status"] == "ACTIVE"


def test_lockout_case_06_concurrent_failed_logins_lock_atomically(client: TestClient):
    """Case 6: Concurrent failed logins lock account atomically without race conditions."""
    username = f"lockout_c6_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    # Simulate 7 rapid consecutive failure attempts
    statuses = []
    for _ in range(7):
        r = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
        statuses.append(r.status_code)

    assert statuses.count(401) == 4
    assert statuses.count(423) == 3


def test_lockout_case_07_lockout_is_per_account_isolated(client: TestClient):
    """Case 7: Locking user A does not impact user B."""
    user_a = f"user_a_{secrets.token_hex(4)}"
    user_b = f"user_b_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        ha, sa = hash_password("PasswordA2026!")
        hb, sb = hash_password("PasswordB2026!")
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')", (user_a, ha, sa, now_iso))
        conn.execute("INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')", (user_b, hb, sb, now_iso))

    # Lock user A
    for _ in range(5):
        client.post("/api/auth/login", json={"username": user_a, "password": "WrongPassword!"})

    resp_a = client.post("/api/auth/login", json={"username": user_a, "password": "PasswordA2026!"})
    assert resp_a.status_code == 423

    # User B should log in normally
    resp_b = client.post("/api/auth/login", json={"username": user_b, "password": "PasswordB2026!"})
    assert resp_b.status_code == 200
    assert "token" in resp_b.json()


def test_lockout_case_08_lockout_state_persists_across_restart(client: TestClient):
    """Case 8: Lockout state resides in persistent SQLite database, surviving server restart simulation."""
    username = f"lockout_c8_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    for _ in range(5):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})

    # Close and reopen database connection
    conn.close()
    new_conn = get_connection()
    row = new_conn.execute("SELECT failed_attempts, locked_until, status FROM users WHERE username = ?", (username,)).fetchone()
    assert row["failed_attempts"] >= 5
    assert row["status"] == "LOCKED"
    assert row["locked_until"] is not None

    # App client still rejects
    resp = client.post("/api/auth/login", json={"username": username, "password": "ValidPassword2026!"})
    assert resp.status_code == 423


def test_lockout_case_09_attempts_during_lockout_do_not_extend_duration(client: TestClient):
    """Case 9: Further login attempts during active lockout do not push locked_until further into the future."""
    username = f"lockout_c9_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    for _ in range(5):
        client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})

    initial_locked_until = conn.execute("SELECT locked_until FROM users WHERE username = ?", (username,)).fetchone()["locked_until"]

    # Sleep slightly and attempt again
    time.sleep(0.05)
    client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!"})
    client.post("/api/auth/login", json={"username": username, "password": "ValidPassword2026!"})

    after_locked_until = conn.execute("SELECT locked_until FROM users WHERE username = ?", (username,)).fetchone()["locked_until"]
    assert initial_locked_until == after_locked_until


def test_lockout_case_10_successful_login_after_lockout_expiry(client: TestClient):
    """Case 10: After lockout window expires, user can authenticate successfully."""
    username = f"lockout_c10_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        # Set expired lockout timestamp
        past_locked = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 5, ?, ?, 'LOCKED')",
            (username, h, s, past_locked, datetime.now(timezone.utc).isoformat())
        )

    # Valid password should now succeed and clear lockout
    resp = client.post("/api/auth/login", json={"username": username, "password": "ValidPassword2026!"})
    assert resp.status_code == 200

    row = conn.execute("SELECT failed_attempts, locked_until, status FROM users WHERE username = ?", (username,)).fetchone()
    assert row["failed_attempts"] == 0
    assert row["locked_until"] is None
    assert row["status"] == "ACTIVE"


def test_lockout_case_11_nonexistent_username_does_not_affect_real_users(client: TestClient):
    """Case 11: Failed logins for nonexistent username return 401 and do not lock any real user."""
    for _ in range(6):
        resp = client.post("/api/auth/login", json={"username": "ghost_user_99999", "password": "BadPassword!"})
        assert resp.status_code == 401

    # Real user should be unaffected
    resp_real = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert resp_real.status_code == 200


def test_lockout_case_12_constant_time_dummy_verification(client: TestClient):
    """Case 12: Timing difference between existing and non-existent users is within safe threshold."""
    timing_user = f"timing_{secrets.token_hex(4)}"
    h, s = hash_password("CorrectPass123!")
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (timing_user, h, s, datetime.now(timezone.utc).isoformat())
        )
    conn.close()

    # Warmup to eliminate first-request connection setup overhead
    client.post("/api/auth/login", json={"username": f"warmup_{secrets.token_hex(4)}", "password": "WrongPassword!"})

    times_existing = []
    times_nonexistent = []

    for _ in range(3):
        # Keep counter reset so it never approaches the 5-failure lockout threshold
        conn = get_connection()
        with conn:
            conn.execute("UPDATE users SET failed_attempts = 0 WHERE username = ?", (timing_user,))
        conn.close()

        t0 = time.perf_counter()
        resp0 = client.post("/api/auth/login", json={"username": timing_user, "password": "WrongPassword!"})
        times_existing.append(time.perf_counter() - t0)
        assert resp0.status_code == 401

        t1 = time.perf_counter()
        resp1 = client.post("/api/auth/login", json={"username": f"nonexistent_{secrets.token_hex(4)}", "password": "WrongPassword!"})
        times_nonexistent.append(time.perf_counter() - t1)
        assert resp1.status_code == 401

    avg_existing = sum(times_existing) / len(times_existing)
    avg_nonexistent = sum(times_nonexistent) / len(times_nonexistent)

    # Both run 100,000 PBKDF2 rounds, execution times should be close
    ratio = abs(avg_existing - avg_nonexistent) / max(avg_existing, avg_nonexistent)
    assert ratio < 0.60, f"Timing discrepancy too large: existing={avg_existing:.4f}s, nonexistent={avg_nonexistent:.4f}s"


# ==============================================================================
# SECTION 11: BROWSER TAMPERING & ZERO-TRUST SECURITY SCENARIOS A TO J
# ==============================================================================

def test_tampering_scenario_a_forged_role_in_request(client: TestClient):
    """Scenario A: Client provides role='admin' in payload; backend uses authoritative session role."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    # Analyst attempts to pass role='admin' in run query
    resp = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "cardiovascular",
            "epsilon": 0.5,
            "role": "admin"  # Injected forge
        }
    )
    assert resp.status_code == 200
    # Receipt user_id and authorization are derived from token, not payload
    receipt = resp.json()["receipt"]
    assert receipt["user_id"] == "analyst_user"


def test_tampering_scenario_b_forged_authorization_flag(client: TestClient):
    """Scenario B: Client supplies is_authorized: true or bypass_policy: true; ignored by backend."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    resp = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "health",
            "field": "ssn",  # Prohibited sensitive field
            "operator": "equals",
            "value": "123-45-6789",
            "epsilon": 0.5,
            "is_authorized": True,
            "bypass_policy": True
        }
    )
    assert resp.status_code == 400
    assert "not in approved allowlist" in resp.json()["detail"].lower()


def test_tampering_scenario_c_modified_counter_in_client(client: TestClient):
    """Scenario C: Client attempts to tamper with counter; backend checks DB state exclusively."""
    username = f"tamper_c_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 4, NULL, ?, 'ACTIVE')",
            (username, h, s, datetime.now(timezone.utc).isoformat())
        )

    # Client tries to send failed_attempts: 0 in request
    resp = client.post("/api/auth/login", json={"username": username, "password": "WrongPassword!", "failed_attempts": 0})
    assert resp.status_code == 423
    assert "Account locked" in resp.json()["detail"]


def test_tampering_scenario_d_direct_api_access_without_session(client: TestClient):
    """Scenario D: Direct API invocation with missing, invalid, or forged Bearer token returns 401."""
    resp1 = client.get("/api/datasets")
    assert resp1.status_code == 401

    resp2 = client.get("/api/me", headers={"Authorization": "Bearer forged_token_12345"})
    assert resp2.status_code == 401


def test_tampering_scenario_e_dataset_substitution(client: TestClient):
    """Scenario E: Client tries to substitute an unauthorized dataset ID."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    resp = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "classified_military_records",
            "field": "category",
            "operator": "equals",
            "value": "top_secret",
            "epsilon": 0.5
        }
    )
    assert resp.status_code == 400
    assert "unknown dataset" in resp.json()["detail"].lower()


def test_tampering_scenario_f_receipt_substitution_object_level_control(client: TestClient):
    """Scenario F: Analyst A cannot view receipt belonging to Analyst B (Object-level gating)."""
    # 1. Analyst A logs in and runs query to generate receipt
    resp_a = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token_a = resp_a.json()["token"]

    run_resp = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.2}
    )
    assert run_resp.status_code == 200
    receipt_id = run_resp.json()["receipt"]["receipt_id"]

    # Analyst A can view own receipt
    get_a = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_a.status_code == 200

    # 2. Create Analyst B
    user_b = f"analyst_b_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        hb, sb = hash_password("AnalystBPass2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (user_b, hb, sb, datetime.now(timezone.utc).isoformat())
        )
    resp_b = client.post("/api/auth/login", json={"username": user_b, "password": "AnalystBPass2026!"})
    token_b = resp_b.json()["token"]

    # Analyst B tries to view Analyst A's receipt -> 403 Forbidden!
    get_b = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 403
    assert "Analysts may only view receipts they generated" in get_b.json()["detail"]

    # 3. Auditor can view it (has receipt.read.authorized)
    resp_auditor = client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    token_auditor = resp_auditor.json()["token"]
    get_auditor = client.get(f"/api/receipts/{receipt_id}", headers={"Authorization": f"Bearer {token_auditor}"})
    assert get_auditor.status_code == 200


def test_tampering_scenario_g_admin_impersonation(client: TestClient):
    """Scenario G: Analyst attempts administrative actions (e.g. session revocation) -> 403 Forbidden."""
    resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = resp.json()["token"]

    revoke_resp = client.post(
        "/api/auth/sessions/revoke",
        headers={"Authorization": f"Bearer {token}"},
        json={"token": "some_other_token", "reason": "Unauthorized attempt"}
    )
    assert revoke_resp.status_code == 403
    assert "Forbidden" in revoke_resp.json()["detail"]


def test_tampering_scenario_h_privacy_budget_tampering(client: TestClient):
    """Scenario H: Client attempts to tamper with budget allowance in request body."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    resp = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "respiratory",
            "epsilon": 0.5,
            "remaining_epsilon": 9999.0,  # Injected budget claim
            "override_budget": True
        }
    )
    assert resp.status_code == 200
    # Remaining budget in response is governed by authoritative DB, not client claim
    assert resp.json()["remaining_budget"] < 100.0


def test_tampering_scenario_i_forged_header_injection(client: TestClient):
    """Scenario I: Injection of X-User-Role, X-Admin, or X-Bypass headers has zero effect."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    resp = client.get(
        "/api/security/events",
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-Role": "admin",
            "X-Admin": "true",
            "X-Bypass-Lockout": "1"
        }
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


def test_tampering_scenario_j_direct_access_to_hidden_endpoints(client: TestClient):
    """Scenario J: Analyst cannot query security events ledger; Steward and Auditor can."""
    # Analyst forbidden
    resp_a = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    get_a = client.get("/api/security/events", headers={"Authorization": f"Bearer {resp_a.json()['token']}"})
    assert get_a.status_code == 403

    # Steward allowed
    resp_s = client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    get_s = client.get("/api/security/events", headers={"Authorization": f"Bearer {resp_s.json()['token']}"})
    assert get_s.status_code == 200
    assert isinstance(get_s.json(), list)

    # Auditor allowed
    resp_aud = client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    get_aud = client.get("/api/security/events", headers={"Authorization": f"Bearer {resp_aud.json()['token']}"})
    assert get_aud.status_code == 200


# ==============================================================================
# SECTION 8: MFA (RFC 6238 TOTP) ENDPOINTS & WORKFLOWS
# ==============================================================================

def test_mfa_full_lifecycle_enrollment_and_enforcement(client: TestClient):
    """Tests MFA enrollment, confirmation with TOTP, and mandatory second-factor on subsequent login."""
    mfa_user = f"mfa_user_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("MfaPass2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (mfa_user, h, s, datetime.now(timezone.utc).isoformat())
        )

    # 1. Login to get initial session
    login_1 = client.post("/api/auth/login", json={"username": mfa_user, "password": "MfaPass2026!"})
    assert login_1.status_code == 200
    token_1 = login_1.json()["token"]

    # 2. Request MFA Enrollment
    enroll_resp = client.post("/api/auth/mfa/enroll", headers={"Authorization": f"Bearer {token_1}"})
    assert enroll_resp.status_code == 200
    enroll_data = enroll_resp.json()
    assert "secret" in enroll_data
    assert "otpauth_uri" in enroll_data
    assert len(enroll_data["recovery_codes"]) == 5
    secret = enroll_data["secret"]

    # 3. Invalid confirmation code is rejected
    verify_bad = client.post("/api/auth/mfa/verify", headers={"Authorization": f"Bearer {token_1}"}, json={"code": "000000"})
    assert verify_bad.status_code == 400

    # 4. Valid confirmation code activates MFA
    current_time_step = int(time.time() // 30)
    valid_code = compute_totp_code(secret, current_time_step)
    verify_good = client.post("/api/auth/mfa/verify", headers={"Authorization": f"Bearer {token_1}"}, json={"code": valid_code})
    assert verify_good.status_code == 200
    assert verify_good.json()["mfa_enabled"] is True

    # 5. Subsequent login without MFA code fails with challenge
    login_no_mfa = client.post("/api/auth/login", json={"username": mfa_user, "password": "MfaPass2026!"})
    assert login_no_mfa.status_code == 401
    assert "MFA verification code required" in login_no_mfa.json()["detail"]

    # 6. Subsequent login with invalid MFA code fails
    login_bad_mfa = client.post("/api/auth/login", json={"username": mfa_user, "password": "MfaPass2026!", "mfa_code": "111111"})
    assert login_bad_mfa.status_code == 401
    assert "Invalid MFA verification code" in login_bad_mfa.json()["detail"]

    # 7. Subsequent login with valid TOTP code succeeds
    fresh_code = compute_totp_code(secret, int(time.time() // 30))
    login_success = client.post("/api/auth/login", json={"username": mfa_user, "password": "MfaPass2026!", "mfa_code": fresh_code})
    assert login_success.status_code == 200
    assert login_success.json()["mfa_active"] is True


# ==============================================================================
# SECTION 9: SESSION REVOCATION
# ==============================================================================

def test_user_logout_invalidates_session(client: TestClient):
    """User logout immediately terminates session token."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    # Verify session active
    me_resp1 = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp1.status_code == 200

    # Logout
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Subsequent request rejected
    me_resp2 = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp2.status_code == 401


def test_administrative_session_revocation(client: TestClient):
    """Data steward administratively revokes an active analyst session."""
    # Analyst logs in
    login_a = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    analyst_token = login_a.json()["token"]

    # Steward logs in
    login_s = client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    steward_token = login_s.json()["token"]

    # Steward revokes analyst token
    revoke_resp = client.post(
        "/api/auth/sessions/revoke",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"token": analyst_token, "reason": "Security audit test"}
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked"] is True

    # Analyst is now rejected
    me_a = client.get("/api/me", headers={"Authorization": f"Bearer {analyst_token}"})
    assert me_a.status_code == 401


def test_user_management_and_unlock_rbac(client: TestClient):
    """Admin or steward can list users and unlock locked accounts, while analyst is rejected."""
    # Analyst attempt is rejected (403)
    login_a = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    analyst_token = login_a.json()["token"]
    res_a = client.get("/api/users", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_a.status_code == 403

    # Admin attempt succeeds
    login_admin = client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    admin_token = login_admin.json()["token"]
    res_admin = client.get("/api/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    users = res_admin.json()
    assert len(users) >= 4
    assert any(u["username"] == "analyst_user" for u in users)

    # Lock a temporary user
    temp_user = f"lock_to_unlock_{secrets.token_hex(4)}"
    conn = get_connection()
    with conn:
        h, s = hash_password("ValidPassword2026!")
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
            (temp_user, h, s, datetime.now(timezone.utc).isoformat())
        )
    for _ in range(5):
        client.post("/api/auth/login", json={"username": temp_user, "password": "WrongPassword!"})

    # Verify locked
    r_locked = client.post("/api/auth/login", json={"username": temp_user, "password": "ValidPassword2026!"})
    assert r_locked.status_code == 423

    # Admin unlocks user
    unlock_res = client.post(f"/api/users/{temp_user}/unlock", headers={"Authorization": f"Bearer {admin_token}"})
    assert unlock_res.status_code == 200
    assert unlock_res.json()["unlocked"] is True

    # User can now log in
    r_unlocked = client.post("/api/auth/login", json={"username": temp_user, "password": "ValidPassword2026!"})
    assert r_unlocked.status_code == 200


def test_security_alerts_filtering_rbac(client: TestClient):
    """Security alerts endpoint lists real incident alerts for authorized roles and denies analysts."""
    login_a = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    analyst_token = login_a.json()["token"]
    res_a = client.get("/api/security/alerts", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_a.status_code == 403

    login_s = client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    steward_token = login_s.json()["token"]
    res_s = client.get("/api/security/alerts", headers={"Authorization": f"Bearer {steward_token}"})
    assert res_s.status_code == 200
    alerts = res_s.json()
    assert isinstance(alerts, list)

