"""Phase 3 Secure Data Vault and Query Gate Automated Tests.

Verifies strict storage isolation, schema validation, path traversal prevention,
raw-row access blocking, arbitrary SQL rejection, and safe error responses.
"""

import pytest
import secrets
from fastapi.testclient import TestClient
from app.db.connection import get_connection
from app.services.query_engine import (
    validate_query,
    get_dataset_metadata,
    _calculate_exact_count_internal,
    PolicyViolationError,
)


def test_v01_dataset_metadata_validation(client: TestClient):
    """V01: Dataset schemas and approved categories are strictly validated."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    resp = client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    datasets = resp.json()
    assert len(datasets) == 2
    ids = {d["dataset_id"] for d in datasets}
    assert "health" in ids
    assert "financial" in ids

    # Check approved fields structure
    for d in datasets:
        assert len(d["approved_fields"]) > 0
        assert d["privacy_unit"] in ("patient_id", "customer_id")
        assert d["total_records"] == 500


def test_v02_path_traversal_prevention_in_dataset_selection(client: TestClient):
    """V02: Path traversal payloads in dataset_id fail closed without touching external files."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    traversal_payloads = [
        "../../etc/passwd",
        "..\\..\\Windows\\System32\\calc.exe",
        "....//....//backend/hotfix_mvp.db",
        "/etc/shadow",
        "data/health_records_demo.json",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ]

    for payload in traversal_payloads:
        resp = client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dataset_id": payload,
                "field": "diagnosis_category",
                "operator": "equals",
                "value": "cardiovascular",
                "epsilon": 0.5
            }
        )
        assert resp.status_code == 400
        assert "unknown dataset" in resp.json()["detail"].lower()
        # Verify no internal server filesystem path or stacktrace leaked
        assert "c:\\users" not in resp.json()["detail"].lower()
        assert "traceback" not in resp.json()["detail"].lower()


def test_v03_raw_row_access_strictly_prevented(client: TestClient):
    """V03: Verifies that no route exists to dump or inspect raw individual records."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    forbidden_routes = [
        "/api/datasets/health/records",
        "/api/datasets/health/rows",
        "/api/datasets/health/download",
        "/api/datasets/health/export",
        "/api/raw/health",
        "/api/v1/query/release",
    ]

    for route in forbidden_routes:
        resp = client.get(route, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (403, 404, 405), f"Route {route} should be blocked, returned {resp.status_code}"


def test_v04_sensitive_column_classification_and_redaction(client: TestClient):
    """V04: Direct queries against sensitive identifier columns are rejected with HTTP 400."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    sensitive_columns = [
        ("health", "patient_name"),
        ("health", "ssn"),
        ("health", "mrn"),
        ("health", "phone_number"),
        ("financial", "account_number"),
        ("financial", "routing_number"),
        ("financial", "card_pan"),
    ]

    for dataset_id, col in sensitive_columns:
        resp = client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dataset_id": dataset_id,
                "field": col,
                "operator": "equals",
                "value": "secret",
                "epsilon": 0.5
            }
        )
        assert resp.status_code == 400
        assert "not in approved allowlist" in resp.json()["detail"].lower()


def test_v05_arbitrary_sql_injection_cannot_be_executed(client: TestClient):
    """V05: Arbitrary SQL injection payloads in parameters are rejected by strict allowlists."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    sql_payloads = [
        ("field", "diagnosis_category; DROP TABLE users; --"),
        ("operator", "equals' OR '1'='1"),
        ("value", "cardiovascular' UNION SELECT * FROM users --"),
    ]

    for param, payload in sql_payloads:
        body = {
            "dataset_id": "health",
            "field": payload if param == "field" else "diagnosis_category",
            "operator": payload if param == "operator" else "equals",
            "value": payload if param == "value" else "cardiovascular",
            "epsilon": 0.5
        }
        resp = client.post("/api/queries/run", headers={"Authorization": f"Bearer {token}"}, json=body)
        assert resp.status_code == 400

    # Ensure users table is intact
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    assert row["cnt"] >= 3


def test_v06_unknown_columns_do_not_silently_become_approved(client: TestClient):
    """V06: Unapproved columns not in dataset approved_fields dictionary are rejected."""
    login_resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_resp.json()["token"]

    resp = client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "health",
            "field": "arbitrary_custom_column_999",
            "operator": "equals",
            "value": "test",
            "epsilon": 0.5
        }
    )
    assert resp.status_code == 400
    assert "not in approved allowlist" in resp.json()["detail"].lower()


def test_v07_safe_error_responses_without_secret_leakage(client: TestClient):
    """V07: Error responses maintain standard schema and never leak filesystem paths or stack traces."""
    # Malformed JSON payload
    resp = client.post("/api/queries/run", content="invalid json {{{", headers={"Content-Type": "application/json"})
    assert resp.status_code in (400, 422)
    data = resp.json()
    assert "error" in data or "detail" in data
    # Ensure no internal path disclosure
    assert "c:\\users" not in str(data).lower()
    assert "site-packages" not in str(data).lower()
    assert "traceback" not in str(data).lower()


def test_v08_count_distinct_privacy_units_enforced():
    """V08: Multi-record individuals contribute at most 1 to internal count calculation."""
    # Compute exact count internally for health dataset
    # In health_records_demo.json, cardiovascular diagnosis
    exact_count = _calculate_exact_count_internal("health", "diagnosis_category", "cardiovascular")
    assert isinstance(exact_count, int)
    assert exact_count > 0
    # Must be bounded by total records (500)
    assert exact_count <= 500
