"""MVP Query Grammar and Allowlist Automated Tests (Tests 7–14)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def analyst_token(client: TestClient) -> str:
    resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    return resp.json()["token"]


def test_07_approved_query_is_accepted(client: TestClient, analyst_token: str):
    """Test 7: An approved count query against health dataset is accepted and returns 200."""
    payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "cardiovascular",
        "epsilon": 0.5,
        "idempotency_key": "test-query-07-approved"
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "release_id" in data
    assert isinstance(data["noisy_count"], int)
    assert data["noisy_count"] >= 0
    assert "receipt" in data
    assert data["policy_check_status"] == "POLICY_CHECK_PASSED"


def test_08_unknown_dataset_is_rejected(client: TestClient, analyst_token: str):
    """Test 8: Query against an unknown or unauthorized dataset is rejected with HTTP 400."""
    payload = {
        "dataset_id": "nonexistent_dataset",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "cardiovascular",
        "epsilon": 0.5
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 400
    assert "Unauthorized or unknown dataset" in resp.json()["detail"]


def test_09_unsupported_operator_is_rejected(client: TestClient, analyst_token: str):
    """Test 9: Query with unsupported operator (e.g. greater_than) is rejected with HTTP 400."""
    payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "greater_than",
        "value": "cardiovascular",
        "epsilon": 0.5
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 400
    assert "Unsupported operator" in resp.json()["detail"]


def test_10_unapproved_field_is_rejected(client: TestClient, analyst_token: str):
    """Test 10: Query for unapproved column (e.g. ssn, patient_id) is rejected with HTTP 400."""
    payload = {
        "dataset_id": "health",
        "field": "patient_id",
        "operator": "equals",
        "value": "P-0001",
        "epsilon": 0.5
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 400
    assert "not in approved allowlist" in resp.json()["detail"]


def test_11_malformed_category_value_is_rejected(client: TestClient, analyst_token: str):
    """Test 11: Query for unapproved category value is rejected with HTTP 400."""
    payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "invented_alien_illness",
        "epsilon": 0.5
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 400
    assert "not an approved category" in resp.json()["detail"]


def test_12_arbitrary_sql_cannot_be_submitted(client: TestClient, analyst_token: str):
    """Test 12: SQL injection strings in value or field are strictly rejected by allowlists."""
    sql_injection = "cardiovascular' OR '1'='1"
    payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": sql_injection,
        "epsilon": 0.5
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 400
    assert "not an approved category" in resp.json()["detail"]


def test_13_raw_records_not_exposed(client: TestClient, analyst_token: str):
    """Test 13: Query response never returns internal raw count or microdata records."""
    payload = {
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "emergency",
        "epsilon": 0.5,
        "idempotency_key": "test-query-13-no-raw"
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "raw_count_internal" not in text
    assert "patient_id" not in resp.json()["receipt"] or resp.json()["receipt"]["patient_id"] is None
    assert "records" not in resp.json()


def test_14_invalid_epsilon_rejected(client: TestClient, analyst_token: str):
    """Test 14: Epsilon values <= 0, > 1.0, or unapproved values are rejected."""
    bad_epsilons = [0.0, -1.0, 999.0, 0.35]
    for eps in bad_epsilons:
        payload = {
            "dataset_id": "health",
            "field": "diagnosis_category",
            "operator": "equals",
            "value": "cardiovascular",
            "epsilon": eps
        }
        resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
        assert resp.status_code == 400
        assert "not permitted" in resp.json()["detail"]
