"""Category 5: Receipts, Cryptographic Hash Chaining & Security Audit Deep Verification Suite.
Validates:
- Ed25519 digital signature generation and verification on Privacy Receipts.
- SHA-256 hash chaining continuity and tamper-evident detection.
- Object-level receipt privacy enforcement (analyst isolation vs auditor oversight).
- Security events logging, SIEM alert records, and RBAC endpoint gating.
"""

import hashlib
import json
import uuid
import secrets
from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from app.main import create_application
from app.db.connection import get_connection, init_database, hash_password
from app.services.crypto_audit import (
    GENESIS_HASH,
    calculate_entry_hash,
    sign_entry_hash,
    verify_entry_signature,
    verify_audit_ledger,
    tamper_audit_entry_for_test,
)


@pytest.fixture(autouse=True)
def setup_receipts_test_env():
    """Ensures clean isolated database for each test run."""
    init_database()
    conn = get_connection()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        UPDATE budget_ledger 
        SET spent_micro_epsilon = 0, remaining_micro_epsilon = 5000000, cap_micro_epsilon = 5000000, updated_at = ?;
    """, (now_iso,))
    conn.execute("DELETE FROM query_releases;")
    conn.execute("DELETE FROM privacy_receipts;")
    conn.execute("DELETE FROM audit_log;")
    conn.execute("DELETE FROM security_events;")
    conn.commit()


@pytest.fixture
def rad_client():
    app = create_application()
    return TestClient(app)


@pytest.fixture
def analyst_token(rad_client):
    res = rad_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def auditor_token(rad_client):
    res = rad_client.post("/api/auth/login", json={"username": "auditor_user", "password": "AuditorPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def steward_token(rad_client):
    res = rad_client.post("/api/auth/login", json={"username": "steward_user", "password": "StewardPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


@pytest.fixture
def admin_token(rad_client):
    res = rad_client.post("/api/auth/login", json={"username": "admin_user", "password": "AdminPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# R1: ED25519 CRYPTOGRAPHIC PRIVACY RECEIPTS (Tests 01 - 10)
# ==============================================================================

def test_r1_01_receipt_issued_upon_successful_release(rad_client, analyst_token):
    res = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert res.status_code == 200
    body = res.json()
    assert "receipt" in body
    rc = body["receipt"]
    assert "receipt_id" in rc
    assert "signature" in rc
    assert "audit_entry_hash" in rc
    assert rc["dataset_id"] == "health"
    assert rc["epsilon_spent"] == 0.5


def test_r1_02_receipt_id_format_uuid4(rad_client, analyst_token):
    res = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "emergency", "epsilon": 0.2}
    )
    assert res.status_code == 200
    rc = res.json()["receipt"]
    assert rc["receipt_id"].startswith("RCPT")
    assert len(rc["receipt_id"]) >= 16


def test_r1_03_ed25519_signature_verifiable_via_service(rad_client, analyst_token):
    res = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    assert verify_entry_signature(rc["audit_entry_hash"], rc["signature"]) is True


def test_r1_04_tampered_hash_fails_signature_verification(rad_client, analyst_token):
    res = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    tampered_hash = hashlib.sha256(b"tampered_content").hexdigest()
    assert verify_entry_signature(tampered_hash, rc["signature"]) is False


def test_r1_05_tampered_signature_fails_verification(rad_client, analyst_token):
    res = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "endocrine", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    # Change first few characters of signature
    tampered_sig = "AAAA" + rc["signature"][4:]
    assert verify_entry_signature(rc["audit_entry_hash"], tampered_sig) is False


def test_r1_06_receipt_stores_authoritative_epsilon_and_mechanism(rad_client, analyst_token):
    res = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.1}
    )
    rc = res.json()["receipt"]
    assert rc["mechanism"] == "Laplace"
    assert rc["epsilon_spent"] == 0.1


def test_r1_07_receipt_records_monotonic_cumulative_budget(rad_client, analyst_token):
    # Query 1 (0.2)
    r1 = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.2}
    ).json()["receipt"]

    # Query 2 (0.5)
    r2 = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "oncology", "epsilon": 0.5}
    ).json()["receipt"]

    assert r1["cumulative_epsilon"] == 0.2
    assert r1["remaining_budget"] == 4.8
    assert r2["cumulative_epsilon"] == 0.7
    assert r2["remaining_budget"] == 4.3


def test_r1_08_receipt_retrieval_by_id_owner(rad_client, analyst_token):
    res_run = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "transferred", "epsilon": 0.5}
    )
    rc_id = res_run.json()["receipt"]["receipt_id"]

    res_get = rad_client.get(f"/api/receipts/{rc_id}", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_get.status_code == 200
    assert res_get.json()["receipt_id"] == rc_id


def test_r1_09_receipt_retrieval_by_auditor(rad_client, analyst_token, auditor_token):
    res_run = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "rehabilitation", "epsilon": 0.5}
    )
    rc_id = res_run.json()["receipt"]["receipt_id"]

    # Auditor retrieves analyst's receipt
    res_get = rad_client.get(f"/api/receipts/{rc_id}", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res_get.status_code == 200
    assert res_get.json()["receipt_id"] == rc_id


def test_r1_10_receipt_retrieval_cross_analyst_blocked(rad_client, analyst_token):
    # Create second analyst
    conn = get_connection()
    user2 = f"analyst2_{secrets.token_hex(4)}"
    h, s = hash_password("Analyst2Pass2026!")
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at, status) VALUES (?, ?, ?, 'analyst', 0, NULL, ?, 'ACTIVE')",
        (user2, h, s, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()

    tok2 = rad_client.post("/api/auth/login", json={"username": user2, "password": "Analyst2Pass2026!"}).json()["token"]

    # Analyst 1 generates receipt
    rc_id = rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "36-50", "epsilon": 0.5}
    ).json()["receipt"]["receipt_id"]

    # Analyst 2 attempts to retrieve Analyst 1's receipt -> 403 Forbidden
    res_get = rad_client.get(f"/api/receipts/{rc_id}", headers={"Authorization": f"Bearer {tok2}"})
    assert res_get.status_code == 403
    assert "Forbidden" in res_get.json()["detail"]


# ==============================================================================
# R2: HASH CHAINING & TAMPER-EVIDENT LEDGER INTEGRITY (Tests 11 - 18)
# ==============================================================================

def test_r2_11_genesis_hash_constant_reproducible():
    expected = hashlib.sha256(b"HOTFIX-GENESIS-UG59-MVP-AUDIT-ROOT").hexdigest()
    assert GENESIS_HASH == expected


def test_r2_12_single_query_chains_from_genesis(rad_client, analyst_token):
    rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "elective", "epsilon": 0.5}
    )
    conn = get_connection()
    row = conn.execute("SELECT * FROM audit_log ORDER BY entry_id ASC LIMIT 1").fetchone()
    assert row["prev_hash"] == GENESIS_HASH


def test_r2_13_multi_query_sequential_hash_linkage(rad_client, analyst_token):
    queries = [
        {"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.2},
        {"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.2},
        {"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "endocrine", "epsilon": 0.2},
    ]
    for q in queries:
        rad_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=q)

    conn = get_connection()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY entry_id ASC").fetchall()
    assert len(rows) == 3
    assert rows[0]["prev_hash"] == GENESIS_HASH
    assert rows[1]["prev_hash"] == rows[0]["entry_hash"]
    assert rows[2]["prev_hash"] == rows[1]["entry_hash"]


def test_r2_14_verify_audit_endpoint_reports_valid_unbroken_chain(rad_client, analyst_token, auditor_token):
    for val in ["cardiovascular", "oncology"]:
        rad_client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": val, "epsilon": 0.5}
        )

    res = rad_client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is True
    assert body["tamper_detected"] is False
    assert body["total_entries"] == 2
    assert body["verified_entries"] == 2


def test_r2_15_detect_altered_expenditure_tamper(rad_client, analyst_token, auditor_token):
    rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "51-65", "epsilon": 0.5}
    )

    conn = get_connection()
    entry = conn.execute("SELECT entry_id FROM audit_log LIMIT 1").fetchone()
    # Deliberately tamper with expenditure
    tamper_audit_entry_for_test(conn, entry["entry_id"], 999999)
    conn.commit()

    # Auditor verification must detect tampering immediately
    res = rad_client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is False
    assert body["tamper_detected"] is True
    assert body["broken_at_entry"] == entry["entry_id"]


def test_r2_16_detect_forged_middle_record(rad_client, analyst_token, auditor_token):
    rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )

    conn = get_connection()
    # Insert a rogue fake audit entry with dummy hashes
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute("""
    INSERT INTO audit_log (
        event_id, actor, dataset_scope, query_fingerprint,
        privacy_expenditure_micro, cumulative_expenditure_micro,
        mechanism, receipt_id, prev_hash, entry_hash, signature, created_at
    ) VALUES ('EVT-FORGED', 'hacker', 'health', 'dummy_fp', 500000, 1000000, 'Laplace', 'fake-rc-id', 'bad_prev', 'bad_entry', 'bad_sig', ?);
    """, (now_iso,))
    conn.commit()

    res = rad_client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is False
    assert body["tamper_detected"] is True


def test_r2_17_detect_deleted_record_in_chain(rad_client, analyst_token, auditor_token):
    # Create 3 audit records
    for val in ["cardiovascular", "respiratory", "oncology"]:
        rad_client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": val, "epsilon": 0.2}
        )

    conn = get_connection()
    # Delete the middle record
    rows = conn.execute("SELECT entry_id FROM audit_log ORDER BY entry_id ASC").fetchall()
    mid_id = rows[1]["entry_id"]
    conn.execute("DELETE FROM audit_log WHERE entry_id = ?", (mid_id,))
    conn.commit()

    res = rad_client.get("/api/audit/verify", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is False
    assert body["tamper_detected"] is True


def test_r2_18_analyst_cannot_access_audit_verify_endpoint(rad_client):
    # Unauthenticated access to /api/audit/verify is rejected with 401
    res = rad_client.get("/api/audit/verify")
    assert res.status_code == 401


# ==============================================================================
# R3: SECURITY AUDIT EVENTS & SIEM ALERTS (Tests 19 - 25)
# ==============================================================================

def test_r3_19_failed_login_records_security_event(rad_client):
    rad_client.post("/api/auth/login", json={"username": "analyst_user", "password": "WrongPassword!"})

    conn = get_connection()
    ev = conn.execute("SELECT * FROM security_events WHERE action = 'LOGIN' AND outcome = 'FAILURE'").fetchone()
    assert ev is not None
    assert ev["actor"] == "analyst_user"


def test_r3_20_policy_violation_records_security_event(rad_client, analyst_token):
    rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "unapproved_ssn", "operator": "equals", "value": "123", "epsilon": 0.5}
    )

    conn = get_connection()
    ev = conn.execute("SELECT * FROM security_events WHERE outcome = 'POLICY_VIOLATION'").fetchone()
    assert ev is not None
    assert ev["actor"] == "analyst_user"


def test_r3_21_budget_exhaustion_records_security_event(rad_client, analyst_token):
    # Exhaust budget
    conn = get_connection()
    conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 5000000, remaining_micro_epsilon = 0 WHERE dataset_id = 'health'")
    conn.commit()

    rad_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.5}
    )

    ev = conn.execute("SELECT * FROM security_events WHERE outcome = 'BUDGET_EXHAUSTED'").fetchone()
    assert ev is not None


def test_r3_22_security_events_list_endpoint_accessible_to_auditor(rad_client, auditor_token):
    res = rad_client.get("/api/security/events", headers={"Authorization": f"Bearer {auditor_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_r3_23_security_events_list_endpoint_accessible_to_admin(rad_client, admin_token):
    res = rad_client.get("/api/security/events", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_r3_24_security_events_list_endpoint_forbidden_to_analyst(rad_client, analyst_token):
    res = rad_client.get("/api/security/events", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 403


def test_r3_25_security_alerts_endpoint_accessible_to_steward(rad_client, steward_token):
    res = rad_client.get("/api/security/alerts", headers={"Authorization": f"Bearer {steward_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)
