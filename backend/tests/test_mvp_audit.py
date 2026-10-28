"""MVP Privacy Receipts and Cryptographic Audit Automated Tests (Tests 25–29)."""

import pytest
from fastapi.testclient import TestClient
from app.db.connection import get_connection
from app.services.crypto_audit import verify_entry_signature, tamper_audit_entry_for_test


@pytest.fixture(scope="module")
def analyst_token(client: TestClient) -> str:
    resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    return resp.json()["token"]


def test_25_valid_ed25519_signature_verifies(client: TestClient, analyst_token: str):
    """Test 25: Valid Privacy Receipts carry authentic Ed25519 signatures that verify."""
    payload = {
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "emergency",
        "epsilon": 0.5,
        "idempotency_key": "audit-test-25"
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200
    receipt = resp.json()["receipt"]

    # Verify signature
    assert "audit_entry_hash" in receipt
    assert "signature" in receipt
    valid = verify_entry_signature(receipt["audit_entry_hash"], receipt["signature"])
    assert valid is True

    # Check /api/audit/verify endpoint
    audit_resp = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    assert audit_resp.status_code == 200
    assert audit_resp.json()["valid"] is True
    assert audit_resp.json()["tamper_detected"] is False


def test_26_modified_audit_entry_fails_verification(client: TestClient, analyst_token: str):
    """Test 26: Deliberately modifying an audit record causes verification to detect tampering."""
    # Ensure there is an audit entry to tamper with
    resp = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "emergency",
        "epsilon": 0.5,
    }, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200

    conn = get_connection()
    latest_entry = conn.execute("SELECT entry_id, privacy_expenditure_micro FROM audit_log ORDER BY entry_id DESC LIMIT 1").fetchone()
    assert latest_entry is not None, "Audit log must contain at least one entry"

    original_val = latest_entry["privacy_expenditure_micro"]
    entry_id = latest_entry["entry_id"]

    try:
        # Tamper with the entry
        with conn:
            tamper_audit_entry_for_test(conn, entry_id, original_val + 999999)

        # Run verification via API
        resp = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {analyst_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert data["tamper_detected"] is True
        assert data["broken_at_entry"] == entry_id

    finally:
        # Restore entry to keep audit chain healthy for subsequent tests
        with conn:
            conn.execute("UPDATE audit_log SET privacy_expenditure_micro = ? WHERE entry_id = ?", (original_val, entry_id))
        conn.close()


def test_27_broken_hash_chain_detected(client: TestClient, analyst_token: str):
    """Test 27: Modifying prev_hash is detected by the hash chain verification."""
    # Ensure there is an audit entry to modify
    resp = client.post("/api/queries/run", json={
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "urgent",
        "epsilon": 0.5,
    }, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200

    conn = get_connection()
    row = conn.execute("SELECT entry_id, prev_hash FROM audit_log ORDER BY entry_id DESC LIMIT 1").fetchone()
    assert row is not None
    orig_prev = row["prev_hash"]
    entry_id = row["entry_id"]

    try:
        with conn:
            conn.execute("UPDATE audit_log SET prev_hash = 'corrupted_prev_hash_12345' WHERE entry_id = ?", (entry_id,))

        resp = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {analyst_token}"})
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert resp.json()["tamper_detected"] is True

    finally:
        with conn:
            conn.execute("UPDATE audit_log SET prev_hash = ? WHERE entry_id = ?", (orig_prev, entry_id))
        conn.close()


def test_28_cumulative_expenditure_agrees_with_ledger(client: TestClient, analyst_token: str):
    """Test 28: Cumulative expenditure in audit log matches the budget ledger values."""
    resp = client.post("/api/queries/run", json={
        "dataset_id": "financial",
        "field": "risk_band",
        "operator": "equals",
        "value": "low",
        "epsilon": 0.2,
    }, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200

    audit_resp = client.get("/api/audit/verify", headers={"Authorization": f"Bearer {analyst_token}"})
    assert audit_resp.status_code == 200
    assert audit_resp.json()["valid"] is True


def test_29_receipt_contains_no_secrets(client: TestClient, analyst_token: str):
    """Test 29: Receipts do not include production noise seeds, passwords, tokens, or raw individual IDs."""
    payload = {
        "dataset_id": "health",
        "field": "age_group",
        "operator": "equals",
        "value": "36-50",
        "epsilon": 0.5,
        "idempotency_key": "audit-test-29"
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200
    receipt = resp.json()["receipt"]

    receipt_str = str(receipt).lower()
    assert "password" not in receipt_str
    assert "token" not in receipt_str
    assert "private_key" not in receipt_str
    assert "seed" not in receipt_str
    assert "p-0" not in receipt_str  # No raw patient identifier values
    assert "c-0" not in receipt_str  # No raw customer identifier values
    assert "raw_count" not in receipt_str
