"""Phase 6 Comprehensive Verification Suite:
Privacy Receipts, Cryptographic Verification, Audit Integrity,
Security Monitoring, Alert Lifecycle, Incident Response, and Fail-Closed Control.

Tests:
1. Canonical receipt serialization & SHA-256 hashing.
2. Ed25519 signature authenticity and key trust boundaries.
3. Cryptographic tampering detection (altering dataset, epsilon, actor, release_id, or signature).
4. Revoked receipt verification rejection.
5. Receipt list API with granular role-based object isolation.
6. Hash-chained audit logs with previous-hash linkages and tamper detection.
7. Paginated audit log retrieval API.
8. Centralized security event capture and detection rule evaluation (brute-force, lockout, 403, budget exhaustion).
9. Alert lifecycle state machine (OPEN -> ACKNOWLEDGED -> RESOLVED).
10. Incident response state machine (NORMAL, RESTRICTED, RELEASES_DISABLED).
11. Fail-closed gate: RELEASES_DISABLED blocks all query releases while preserving diagnostics.
12. Fail-closed gate: RESTRICTED blocks excessive epsilon (> 0.50).
13. Authorized recovery procedure: RELEASES_DISABLED -> RESTRICTED -> NORMAL.
"""

import hashlib
import json
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

from app.main import create_application
from app.db.connection import get_connection, init_database
from app.services.crypto_audit import (
    canonicalize_receipt,
    compute_receipt_hash,
    sign_entry_hash,
    verify_entry_signature,
    verify_receipt_cryptographic,
    verify_audit_ledger,
    get_audit_entries,
    tamper_audit_entry_for_test,
    TRUSTED_KEY_ID,
    RECEIPT_SCHEMA_VERSION,
)
from app.services.incident_service import (
    get_incident_status,
    transition_incident_state,
    list_security_alerts,
    get_security_alert_detail,
    acknowledge_security_alert,
    resolve_security_alert,
    trigger_automated_fail_closed,
    evaluate_detection_rules,
    STATE_NORMAL,
    STATE_RESTRICTED,
    STATE_RELEASES_DISABLED,
    IncidentStateError,
)
from app.services.query_engine import execute_query_pipeline, BudgetExhaustedError


@pytest.fixture(autouse=True)
def setup_phase6_env():
    """Isolates each test with a pristine database and restored incident state."""
    init_database()
    conn = get_connection()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute("""
            UPDATE budget_ledger 
            SET spent_micro_epsilon = 0, remaining_micro_epsilon = 5000000, cap_micro_epsilon = 5000000, updated_at = ?;
        """, (now_iso,))
        conn.execute("DELETE FROM privacy_receipts;")
        conn.execute("DELETE FROM query_releases;")
        conn.execute("DELETE FROM audit_log;")
        conn.execute("DELETE FROM security_alerts;")
        conn.execute("DELETE FROM security_events;")
        conn.execute("DELETE FROM incident_log;")
        conn.execute("""
            UPDATE incident_state 
            SET current_state = 'NORMAL', trigger_source = 'TEST_SETUP', reason = 'Test environment reset to operational state.', updated_by = 'system', updated_at = ?
            WHERE id = 1;
        """, (now_iso,))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def client():
    app = create_application()
    return TestClient(app)


@pytest.fixture
def analyst_token(client):
    res = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def steward_token(client):
    res = client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def auditor_token(client):
    res = client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def admin_token(client):
    res = client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# SECTION A: RECEIPT CANONICALIZATION & CRYPTOGRAPHIC VERIFICATION
# ==============================================================================

def test_p6_01_canonical_receipt_serialization_deterministic():
    """Verify that canonical receipt representation is deterministic and field-order invariant."""
    sample_a = {
        "receipt_id": "RCPT-1001",
        "release_id": "REL-2001",
        "user_id": "analyst_user",
        "dataset_id": "health",
        "dataset_version": "1.0.0",
        "query_fingerprint": "fp_abc123",
        "query_description": "COUNT_DISTINCT(patient_id) WHERE diagnosis = 'cardio'",
        "mechanism": "Laplace",
        "epsilon_spent": 0.5,
        "cumulative_epsilon": 0.5,
        "remaining_budget": 4.5,
        "policy_check_status": "POLICY_CHECK_PASSED",
        "audit_entry_hash": "audit_hash_xyz",
        "key_id": TRUSTED_KEY_ID,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "timestamp": "2026-10-29T00:00:00Z"
    }

    # Same data, reversed dictionary insertion order
    sample_b = dict(reversed(list(sample_a.items())))

    canon_a = canonicalize_receipt(sample_a)
    canon_b = canonicalize_receipt(sample_b)

    assert canon_a == canon_b
    assert "RCPT-1001" in canon_a
    assert "0.5000" in canon_a
    assert TRUSTED_KEY_ID in canon_a


def test_p6_02_receipt_hashing_sha256():
    """Verify receipt SHA-256 calculation produces 64-character lowercase hexadecimal hash."""
    sample = {
        "receipt_id": "RCPT-test",
        "release_id": "REL-test",
        "user_id": "analyst_user",
        "dataset_id": "health",
        "dataset_version": "1.0.0",
        "query_fingerprint": "abc",
        "query_description": "test",
        "mechanism": "Laplace",
        "epsilon_spent": 0.5,
        "cumulative_epsilon": 0.5,
        "remaining_budget": 4.5,
        "policy_check_status": "POLICY_CHECK_PASSED",
        "audit_entry_hash": "hash123",
        "key_id": TRUSTED_KEY_ID,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "timestamp": "2026-10-29T00:00:00Z"
    }
    h = compute_receipt_hash(sample)
    assert len(h) == 64
    assert h == h.lower()
    assert int(h, 16) > 0


def test_p6_03_ed25519_signature_generation_and_verification():
    """Verify Ed25519 enclave keypair correctly signs and verifies arbitrary target hashes."""
    msg_hash = hashlib.sha256(b"test_payload_for_signing").hexdigest()
    sig = sign_entry_hash(msg_hash)
    assert isinstance(sig, str)
    assert len(sig) > 60
    assert verify_entry_signature(msg_hash, sig) is True


def test_p6_04_unknown_or_bogus_signature_rejected():
    """Verify that a forged or altered Ed25519 signature fails verification."""
    msg_hash = hashlib.sha256(b"authentic_message").hexdigest()
    sig = sign_entry_hash(msg_hash)

    # Corrupt one character in the base64 signature
    corrupt_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
    assert verify_entry_signature(msg_hash, corrupt_sig) is False

    # Signature against wrong message hash
    wrong_hash = hashlib.sha256(b"different_message").hexdigest()
    assert verify_entry_signature(wrong_hash, sig) is False


# ==============================================================================
# SECTION B: CRYPTOGRAPHIC TAMPERING & RECEIPT INTEGRITY
# ==============================================================================

def test_p6_05_authentic_receipt_verifies_completely(client, analyst_token):
    """Test that a newly issued Privacy Receipt passes 100% of cryptographic and relational integrity checks."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert res.status_code == 200
    rc = res.json()["receipt"]
    receipt_id = rc["receipt_id"]

    v_res = client.post(
        f"/api/receipts/{receipt_id}/verify",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert v_res.status_code == 200
    v_data = v_res.json()

    assert v_data["is_valid"] is True
    assert v_data["verification_status"] == "VERIFIED_AUTHENTIC"
    assert v_data["checks"]["receipt_found"] is True
    assert v_data["checks"]["schema_valid"] is True
    assert v_data["checks"]["not_revoked"] is True
    assert v_data["checks"]["hash_match"] is True
    assert v_data["checks"]["signature_valid"] is True
    assert v_data["checks"]["key_trusted"] is True
    assert v_data["checks"]["release_linked"] is True
    assert v_data["checks"]["audit_linked"] is True


def test_p6_06_tampered_receipt_epsilon_spent_fails_verification(client, analyst_token):
    """Test that altering epsilon_spent in database causes canonical hash mismatch and fails verification."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    receipt_id = rc["receipt_id"]

    # Deliberately tamper with epsilon_spent in SQLite database
    conn = get_connection()
    try:
        conn.execute("UPDATE privacy_receipts SET epsilon_spent = 0.1 WHERE receipt_id = ?", (receipt_id,))
        conn.commit()
    finally:
        conn.close()

    v_res = client.post(f"/api/receipts/{receipt_id}/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    assert v_res.status_code == 200
    v_data = v_res.json()

    assert v_data["is_valid"] is False
    assert v_data["verification_status"] == "VERIFICATION_FAILED"
    assert v_data["checks"]["hash_match"] is False
    assert "hash mismatch" in v_data["error_message"].lower()


def test_p6_07_tampered_receipt_dataset_id_fails_verification(client, analyst_token):
    """Test that modifying the dataset scope fails both hash and release linkage checks."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    receipt_id = rc["receipt_id"]

    conn = get_connection()
    try:
        conn.execute("UPDATE privacy_receipts SET dataset_id = 'financial' WHERE receipt_id = ?", (receipt_id,))
        conn.commit()
    finally:
        conn.close()

    v_res = client.post(f"/api/receipts/{receipt_id}/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    v_data = v_res.json()

    assert v_data["is_valid"] is False
    assert v_data["checks"]["release_linked"] is False


def test_p6_08_tampered_receipt_signature_fails_verification(client, analyst_token):
    """Test that replacing the Ed25519 signature with invalid bytes fails verification."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    receipt_id = rc["receipt_id"]

    conn = get_connection()
    try:
        conn.execute("UPDATE privacy_receipts SET signature = 'bogus_forged_sig_12345' WHERE receipt_id = ?", (receipt_id,))
        conn.commit()
    finally:
        conn.close()

    v_res = client.post(f"/api/receipts/{receipt_id}/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    v_data = v_res.json()

    assert v_data["is_valid"] is False
    assert v_data["checks"]["signature_valid"] is False
    assert "signature invalid" in v_data["error_message"].lower()


def test_p6_09_revoked_receipt_fails_verification(client, analyst_token):
    """Test that an administratively revoked receipt is detected and flagged."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    receipt_id = rc["receipt_id"]

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE privacy_receipts SET is_revoked = 1, revoked_reason = 'Suspected analyst key exposure' WHERE receipt_id = ?",
            (receipt_id,)
        )
        conn.commit()
    finally:
        conn.close()

    v_res = client.post(f"/api/receipts/{receipt_id}/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    v_data = v_res.json()

    assert v_data["is_valid"] is False
    assert v_data["checks"]["not_revoked"] is False
    assert "revoked" in v_data["error_message"].lower()


# ==============================================================================
# SECTION C: HASH-CHAIN INTEGRITY & AUDIT TRAIL API
# ==============================================================================

def test_p6_10_audit_hash_chain_sequential_linkage(client, analyst_token):
    """Test that multiple releases establish sequential prev_hash -> entry_hash cryptographic linkages."""
    r1 = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    ).json()["receipt"]

    r2 = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "emergency", "epsilon": 0.5}
    ).json()["receipt"]

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY entry_id ASC").fetchall()
        assert len(rows) == 2
        # First entry links to Genesis Hash
        from app.services.crypto_audit import GENESIS_HASH
        assert rows[0]["prev_hash"] == GENESIS_HASH
        # Second entry links to first entry's hash
        assert rows[1]["prev_hash"] == rows[0]["entry_hash"]

        # Ledger verification passes
        ledger_res = verify_audit_ledger(conn)
        assert ledger_res["valid"] is True
        assert ledger_res["verified_entries"] == 2
        assert ledger_res["tamper_detected"] is False
    finally:
        conn.close()


def test_p6_11_audit_tamper_detected_at_exact_entry(client, analyst_token):
    """Test that tampering with an audit entry in the chain is pinpointed to the exact entry_id."""
    for val in ["cardiovascular", "emergency", "18-35"]:
        field = "diagnosis_category" if val == "cardiovascular" else ("admission_type" if val == "emergency" else "age_group")
        client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": field, "operator": "equals", "value": val, "epsilon": 0.5}
        )

    conn = get_connection()
    try:
        rows = conn.execute("SELECT entry_id FROM audit_log ORDER BY entry_id ASC").fetchall()
        assert len(rows) == 3
        target_entry_id = rows[1]["entry_id"]

        # Tamper with the 2nd entry in the chain
        tamper_audit_entry_for_test(conn, entry_id=target_entry_id, new_expenditure_micro=999999)
        conn.commit()

        report = verify_audit_ledger(conn)
        assert report["valid"] is False
        assert report["tamper_detected"] is True
        assert report["broken_at_entry"] == target_entry_id
        assert f"Entry hash mismatch at entry {target_entry_id}" in report["error_message"]
    finally:
        conn.close()


def test_p6_12_audit_entries_paginated_list_endpoint(client, auditor_token, analyst_token):
    """Test GET /api/audit/entries returns paginated entries with total count and search capability."""
    client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )

    res = client.get("/api/audit/entries?limit=10&offset=0", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["actor"] == "analyst_user"
    assert entry["dataset_scope"] == "health"
    assert entry["privacy_expenditure_micro"] == 500000


# ==============================================================================
# SECTION D: AUTHORIZATION & OBJECT-LEVEL ACCESS CONTROL
# ==============================================================================

def test_p6_13_analyst_cannot_access_receipt_of_another_user(client, analyst_token, steward_token):
    """Test that Analyst role receives 403 Forbidden when trying to access another user's receipt."""
    # Steward runs query or creates receipt
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc_id = res.json()["receipt"]["receipt_id"]

    # Deliberately attribute receipt to steward_user in DB
    conn = get_connection()
    try:
        conn.execute("UPDATE privacy_receipts SET user_id = 'steward_user' WHERE receipt_id = ?", (rc_id,))
        conn.commit()
    finally:
        conn.close()

    # Analyst requests receipt belonging to steward_user -> 403
    forbidden_res = client.get(f"/api/receipts/{rc_id}", headers={"Authorization": f"Bearer {analyst_token}"})
    assert forbidden_res.status_code == 403
    assert "belongs to another analyst" in forbidden_res.json()["detail"].lower()


def test_p6_14_auditor_can_inspect_any_receipt(client, analyst_token, auditor_token):
    """Test that Auditor with 'receipt.read.authorized' can access any receipt regardless of owner."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc_id = res.json()["receipt"]["receipt_id"]

    # Auditor accesses analyst's receipt -> 200 OK
    audit_res = client.get(f"/api/receipts/{rc_id}", headers={"Authorization": f"Bearer {auditor_token}"})
    assert audit_res.status_code == 200
    assert audit_res.json()["receipt_id"] == rc_id


def test_p6_15_receipt_list_endpoint_filters_by_analyst_ownership(client, analyst_token, steward_token):
    """Test GET /api/receipts returns only own receipts for analyst."""
    client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )

    res = client.get("/api/receipts", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["receipts"][0]["user_id"] == "analyst_user"


# ==============================================================================
# SECTION E: SECURITY MONITORING, DETECTION RULES & ALERTS
# ==============================================================================

def test_p6_16_brute_force_detection_rule(client):
    """Test that 3 consecutive failed login attempts trigger RULE_BRUTE_FORCE_BURST alert."""
    for _ in range(3):
        client.post("/api/auth/login", json={"username": "target_user_xyz", "password": "wrong_password"})

    alerts = list_security_alerts(rule_id="RULE_BRUTE_FORCE_BURST")
    assert len(alerts) >= 1
    alert = alerts[0]
    assert alert["rule_id"] == "RULE_BRUTE_FORCE_BURST"
    assert alert["severity"] == "MEDIUM"
    assert alert["status"] == "OPEN"


def test_p6_17_account_lockout_triggers_high_severity_alert(client):
    """Test that reaching 5 failed logins triggers RULE_ACCOUNT_LOCKOUT alert with HIGH severity."""
    from app.db.connection import get_connection, hash_password
    conn = get_connection()
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        h, salt = hash_password("ValidPassword2026!")
        conn.execute("""
        INSERT OR REPLACE INTO users (username, user_id, password_hash, salt, role, status, failed_attempts, locked_until, created_at, last_password_change)
        VALUES ('lockout_target_p6', 'USR-lockout-001', ?, ?, 'analyst', 'ACTIVE', 0, NULL, ?, ?);
        """, (h, salt, now_iso, now_iso))
        conn.commit()
    finally:
        conn.close()

    for _ in range(5):
        client.post("/api/auth/login", json={"username": "lockout_target_p6", "password": "bad_password"})

    alerts = list_security_alerts(severity_filter="HIGH")
    lockout_alerts = [a for a in alerts if a["rule_id"] == "RULE_ACCOUNT_LOCKOUT"]
    assert len(lockout_alerts) >= 1
    assert lockout_alerts[0]["severity"] == "HIGH"


def test_p6_18_unauthorized_role_attempt_triggers_alert(client, analyst_token):
    """Test that attempting an administrative action without permission generates an alert."""
    # Analyst attempts to unlock user (requires user.manage)
    res = client.post(
        "/api/users/some_user/unlock",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert res.status_code == 403

    alerts = list_security_alerts(rule_id="RULE_UNAUTHORIZED_ACCESS")
    assert len(alerts) >= 1
    assert alerts[0]["rule_id"] == "RULE_UNAUTHORIZED_ACCESS"


def test_p6_19_budget_exhaustion_attempt_triggers_alert(client, analyst_token):
    """Test that attempting a query after budget exhaustion generates a monitoring alert."""
    # Exhaust budget (5 releases of 1.0 eps)
    for val in ["cardiovascular", "respiratory", "neurological", "endocrine", "emergency"]:
        field = "admission_type" if val == "emergency" else "diagnosis_category"
        client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": field, "operator": "equals", "value": val, "epsilon": 1.0}
        )

    # 6th query fails with 429
    blocked = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": 1.0}
    )
    assert blocked.status_code == 429

    alerts = list_security_alerts(rule_id="RULE_BUDGET_EXHAUSTION")
    assert len(alerts) >= 1
    assert alerts[0]["rule_id"] == "RULE_BUDGET_EXHAUSTION"


# ==============================================================================
# SECTION F: ALERT LIFECYCLE MANAGEMENT (ACKNOWLEDGE & RESOLVE)
# ==============================================================================

def test_p6_20_alert_acknowledgment_workflow(client, steward_token):
    """Test transitioning an open alert to ACKNOWLEDGED status with reviewer assignment."""
    from app.services.incident_service import create_security_alert
    alert_id = create_security_alert(
        rule_id="TEST_RULE_01",
        title="Test Investigation Alert",
        severity="MEDIUM",
        actor="test_actor",
        details="Sample trigger for lifecycle test"
    )

    ack_res = client.post(
        f"/api/security/alerts/{alert_id}/acknowledge",
        headers={"Authorization": f"Bearer {steward_token}"}
    )
    assert ack_res.status_code == 200
    data = ack_res.json()
    assert data["status"] == "ACKNOWLEDGED"
    assert data["acknowledged_by"] == "steward_user"
    assert data["acknowledged_at"] is not None


def test_p6_21_alert_resolution_requires_notes_and_perm(client, steward_token, analyst_token):
    """Test that resolving an alert requires mandatory resolution notes and steward/admin permissions."""
    from app.services.incident_service import create_security_alert
    alert_id = create_security_alert(
        rule_id="TEST_RULE_02",
        title="Test Resolution Alert",
        severity="LOW",
        actor="test_actor",
        details="Sample trigger for resolution test"
    )

    # Analyst lacks permission -> 403
    unauth = client.post(
        f"/api/security/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"resolution_notes": "Should fail"}
    )
    assert unauth.status_code == 403

    # Empty notes rejected -> 422 or 400
    empty_notes = client.post(
        f"/api/security/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"resolution_notes": "sh"}
    )
    assert empty_notes.status_code in (400, 422)

    # Valid resolution succeeds
    resolved = client.post(
        f"/api/security/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"resolution_notes": "Confirmed expected testing activity. False positive ruled out.", "status": "RESOLVED"}
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolved_by"] == "steward_user"


# ==============================================================================
# SECTION G: INCIDENT RESPONSE STATE MACHINE & FAIL-CLOSED CONTROL
# ==============================================================================

def test_p6_22_incident_status_endpoint_returns_operational(client, analyst_token):
    """Test GET /api/incident/status returns active operational state."""
    res = client.get("/api/incident/status", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["current_state"] == "NORMAL"
    assert data["releases_allowed"] is True
    assert data["max_permitted_epsilon"] == 1.0


def test_p6_23_incident_transition_normal_to_restricted(client, steward_token):
    """Test transitioning from NORMAL to RESTRICTED caps maximum allowable epsilon at 0.50."""
    res = client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"new_state": "RESTRICTED", "reason": "Precautionary elevated privacy restrictions during scheduled audit."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_state"] == "RESTRICTED"
    assert data["max_permitted_epsilon"] == 0.50
    assert data["releases_allowed"] is True


def test_p6_24_restricted_mode_rejects_high_epsilon_query(client, steward_token, analyst_token):
    """Test that queries requesting epsilon > 0.50 are blocked when gateway is in RESTRICTED mode."""
    # Shift into RESTRICTED
    client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"new_state": "RESTRICTED", "reason": "Restricting query release budget for testing."}
    )

    # Query with eps = 1.0 is rejected
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 1.0}
    )
    assert res.status_code == 400
    assert "restricted incident state" in res.json()["detail"].lower()

    # Query with eps = 0.50 succeeds
    res_ok = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert res_ok.status_code == 200


def test_p6_25_incident_transition_to_releases_disabled(client, steward_token):
    """Test transitioning gateway to RELEASES_DISABLED state."""
    res = client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"new_state": "RELEASES_DISABLED", "reason": "Emergency suspension: investigating unusual query anomaly."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_state"] == "RELEASES_DISABLED"
    assert data["releases_allowed"] is False
    assert data["max_permitted_epsilon"] == 0.0


def test_p6_26_releases_disabled_blocks_all_query_releases_fail_closed(client, steward_token, analyst_token):
    """Test that RELEASES_DISABLED immediately terminates query releases fail-closed with HTTP 503."""
    client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"new_state": "RELEASES_DISABLED", "reason": "Suspending all query releases fail-closed."}
    )

    # Even a small epsilon query is completely blocked
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.1}
    )
    assert res.status_code == 503
    assert "privacy releases suspended fail-closed" in res.json()["detail"].lower()


def test_p6_27_releases_disabled_preserves_diagnostic_and_audit_access(client, steward_token, auditor_token):
    """Test that critical diagnostic, health, and audit inspection endpoints remain accessible during RELEASES_DISABLED."""
    client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {steward_token}"},
        json={"new_state": "RELEASES_DISABLED", "reason": "Fail-closed lock for diagnostics verification."}
    )

    # Diagnostic probe: 200 OK
    h_res = client.get("/health")
    assert h_res.status_code == 200

    # System status: 200 OK
    s_res = client.get("/api/system/status")
    assert s_res.status_code == 200

    # Audit verification: 200 OK
    a_res = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert a_res.status_code == 200


def test_p6_28_unauthorized_user_cannot_transition_incident_state(client, analyst_token):
    """Test that an Analyst cannot change the gateway's incident state (403 Forbidden)."""
    res = client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"new_state": "RELEASES_DISABLED", "reason": "Unauthorized analyst attempt."}
    )
    assert res.status_code == 403


def test_p6_29_authorized_recovery_workflow_restores_normal_operations(client, admin_token, analyst_token):
    """Test multi-step incident recovery: RELEASES_DISABLED -> RESTRICTED -> NORMAL."""
    # 1. Trigger suspension
    client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_state": "RELEASES_DISABLED", "reason": "Simulated incident containment."}
    )

    # 2. Step down to RESTRICTED
    step_down = client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_state": "RESTRICTED", "reason": "Investigation complete. Restoring under restricted observation."}
    )
    assert step_down.status_code == 200
    assert step_down.json()["current_state"] == "RESTRICTED"

    # 3. Restore to NORMAL
    restored = client.post(
        "/api/incident/transition",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_state": "NORMAL", "reason": "All verification checks passed. Fully restored to normal operations."}
    )
    assert restored.status_code == 200
    assert restored.json()["current_state"] == "NORMAL"

    # 4. Normal query execution works again
    q_res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 1.0}
    )
    assert q_res.status_code == 200


def test_p6_30_receipt_verification_api_returns_checks_breakdown(client, analyst_token):
    """Test that POST /api/receipts/{receipt_id}/verify returns structured verification checks."""
    res = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    rc_id = res.json()["receipt"]["receipt_id"]

    v_res = client.post(f"/api/receipts/{rc_id}/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    assert v_res.status_code == 200
    v_data = v_res.json()

    assert "checks" in v_data
    checks = v_data["checks"]
    assert checks["receipt_found"] is True
    assert checks["signature_valid"] is True
    assert checks["hash_match"] is True
    assert checks["release_linked"] is True
    assert checks["audit_linked"] is True
    assert checks["not_revoked"] is True
    assert v_data["key_id"] == TRUSTED_KEY_ID
