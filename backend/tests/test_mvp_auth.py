"""MVP Authentication and Authorization Automated Tests (Tests 1–6)."""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.db.connection import get_connection


def test_01_valid_login_succeeds(client: TestClient):
    """Test 1: Valid credentials for analyst, steward, and auditor return token and correct role."""
    roles = [
        ("analyst_user", "AnalystPass2026!", "analyst"),
        ("steward_user", "StewardPass2026!", "data_steward"),
        ("auditor_user", "AuditorPass2026!", "auditor"),
    ]
    for username, password, expected_role in roles:
        resp = client.post("/api/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data and len(data["token"]) >= 32
        assert data["username"] == username
        assert data["role"] == expected_role
        assert "expires_at" in data


def test_02_invalid_login_fails(client: TestClient):
    """Test 2: Invalid password fails with HTTP 401 without revealing user existence."""
    resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "WrongPassword!"})
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]


def test_03_five_failed_attempts_trigger_temporary_lockout(client: TestClient):
    """Test 3: Five consecutive failed attempts trigger temporary lockout (HTTP 423)."""
    # Create or reset a dedicated test user
    username = "lockout_test_user"
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        from app.db.connection import hash_password
        h, s = hash_password("CorrectPass2026!")
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at) VALUES (?, ?, ?, 'analyst', 0, NULL, ?)",
            (username, h, s, now_iso)
        )

    # 4 failed attempts
    for _ in range(4):
        resp = client.post("/api/auth/login", json={"username": username, "password": "BadPassword"})
        assert resp.status_code == 401

    # 5th failed attempt should trigger lockout (423)
    resp5 = client.post("/api/auth/login", json={"username": username, "password": "BadPassword"})
    assert resp5.status_code == 423
    assert "Account locked" in resp5.json()["detail"]

    # 6th attempt with correct password should still be rejected as locked
    resp6 = client.post("/api/auth/login", json={"username": username, "password": "CorrectPass2026!"})
    assert resp6.status_code == 423


def test_04_unauthorized_user_cannot_access_protected_endpoints(client: TestClient):
    """Test 4: Requests without valid Authorization header are rejected with HTTP 401."""
    resp1 = client.get("/api/datasets")
    assert resp1.status_code == 401

    resp2 = client.post("/api/queries/run", json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5})
    assert resp2.status_code == 401


def test_05_role_based_access_control(client: TestClient):
    """Test 5: Validates role profiles via /api/me and role-based permissions."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    me_resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "analyst_user"
    assert me_resp.json()["role"] == "analyst"


def test_06_expired_sessions_are_rejected(client: TestClient):
    """Test 6: Expired session tokens return HTTP 401."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    # Deliberately expire the token in database
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    conn = get_connection()
    with conn:
        conn.execute("UPDATE sessions SET expires_at = ? WHERE token = ?", (past_iso, token))

    resp = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()

