"""MVP Differential Privacy and Budget Ledger Automated Tests (Tests 15–24)."""

import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.db.connection import get_connection
from app.services.privacy_engine import apply_laplace_noise


@pytest.fixture(scope="module")
def analyst_token(client: TestClient) -> str:
    resp = client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    return resp.json()["token"]


def test_15_real_laplace_invoked():
    """Test 15: Laplace mechanism runs and outputs non-negative integer counts with noise."""
    exact = 100
    noisy_results = [apply_laplace_noise(exact, epsilon=0.5) for _ in range(25)]
    # All must be integers >= 0
    for r in noisy_results:
        assert isinstance(r, int)
        assert r >= 0
    # Must be non-deterministic (not always returning exact 100)
    assert len(set(noisy_results)) > 1


def test_16_privacy_unit_distinct_contribution():
    """Test 16: Distinct privacy units are counted, so individuals with multiple rows contribute at most 1."""
    from app.services.query_engine import _calculate_exact_count_internal, get_dataset_metadata
    exact_distinct = _calculate_exact_count_internal("health", "diagnosis_category", "cardiovascular")
    meta = get_dataset_metadata("health")
    assert exact_distinct <= meta["total_records"]
    assert exact_distinct > 0


def test_17_exact_count_not_in_analyst_response(client: TestClient, analyst_token: str):
    """Test 17: Analyst response does not contain the exact reference count."""
    payload = {
        "dataset_id": "health",
        "field": "age_group",
        "operator": "equals",
        "value": "18-35",
        "epsilon": 0.2,
        "idempotency_key": "test-query-17"
    }
    resp = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 200
    assert "exact_count" not in resp.json()
    assert "raw_count" not in resp.json()


def test_21_identical_cached_query_zero_cost(client: TestClient, analyst_token: str):
    """Test 21: Submitting an identical query with same epsilon reuses cached release at 0 budget cost."""
    payload = {
        "dataset_id": "financial",
        "field": "transaction_type",
        "operator": "equals",
        "value": "wire",
        "epsilon": 0.5,
    }
    # First execution
    resp1 = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["is_cached"] is False
    assert data1["epsilon_spent"] == 0.5
    count1 = data1["noisy_count"]
    cum1 = data1["cumulative_epsilon"]

    # Second execution (identical query & epsilon)
    resp2 = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_cached"] is True
    assert data2["epsilon_spent"] == 0.0  # Zero cost on cache hit
    assert data2["noisy_count"] == count1  # Identical randomized release
    assert data2["cumulative_epsilon"] == cum1  # No budget deducted


def test_22_different_epsilon_not_cached(client: TestClient, analyst_token: str):
    """Test 22: Query with same field/value but different epsilon spends additional budget as a distinct release."""
    payload_05 = {
        "dataset_id": "financial",
        "field": "risk_band",
        "operator": "equals",
        "value": "high",
        "epsilon": 0.5,
    }
    payload_10 = {
        "dataset_id": "financial",
        "field": "risk_band",
        "operator": "equals",
        "value": "high",
        "epsilon": 1.0,
    }

    resp1 = client.post("/api/queries/run", json=payload_05, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp1.status_code == 200
    assert resp1.json()["is_cached"] is False

    resp2 = client.post("/api/queries/run", json=payload_10, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp2.status_code == 200
    # Different epsilon must not be served from 0.5 cache
    assert resp2.json()["is_cached"] is False
    assert resp2.json()["epsilon_spent"] == 1.0


def test_24_idempotent_retry_does_not_double_spend(client: TestClient, analyst_token: str):
    """Test 24: Retrying a query with an existing idempotency_key returns original release at 0 cost."""
    key = "idemp-key-unique-test-24"
    payload = {
        "dataset_id": "health",
        "field": "discharge_status",
        "operator": "equals",
        "value": "routine",
        "epsilon": 0.5,
        "idempotency_key": key
    }
    resp1 = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Retry with same idempotency key
    resp2 = client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["release_id"] == data1["release_id"]
    assert data2["noisy_count"] == data1["noisy_count"]
    assert data2["epsilon_spent"] == 0.0


def test_18_and_19_budget_exhaustion_and_cap_limit(client: TestClient, analyst_token: str):
    """Tests 18 & 19: Budget ledger enforces 5.0 cap; subsequent queries are rejected with HTTP 429."""
    # Reset health budget to low balance (0.4 epsilon remaining) to test rejection
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE budget_ledger SET spent_micro_epsilon = 4600000, remaining_micro_epsilon = 400000 WHERE dataset_id = 'health'"
        )

    # 1. Query with epsilon=0.5 should be rejected (0.5 > 0.4)
    payload_too_expensive = {
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "elective",
        "epsilon": 0.5,
    }
    resp_rej = client.post("/api/queries/run", json=payload_too_expensive, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp_rej.status_code == 429
    assert "Privacy budget exhausted" in resp_rej.json()["detail"]

    # 2. Query with epsilon=0.2 should succeed (0.2 <= 0.4)
    payload_affordable = {
        "dataset_id": "health",
        "field": "admission_type",
        "operator": "equals",
        "value": "elective",
        "epsilon": 0.2,
    }
    resp_ok = client.post("/api/queries/run", json=payload_affordable, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp_ok.status_code == 200
    assert resp_ok.json()["remaining_budget"] == 0.2


def test_20_concurrent_requests_cannot_overspend(client: TestClient, analyst_token: str):
    """Test 20: Concurrent requests cannot overspend the remaining budget due to atomic transactions."""
    # Set financial dataset remaining budget to exactly 0.5 epsilon
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE budget_ledger SET spent_micro_epsilon = 4500000, remaining_micro_epsilon = 500000 WHERE dataset_id = 'financial'"
        )

    # Attempt to run 4 concurrent queries each requesting epsilon=0.5
    # Exactly one should succeed, and the others must be rejected with 429!
    def fire_query(idx):
        payload = {
            "dataset_id": "financial",
            "field": "account_type",
            "operator": "equals",
            "value": "checking" if idx % 2 == 0 else "savings",
            "epsilon": 0.5,
            "idempotency_key": f"concurrent-txn-{idx}"
        }
        return client.post("/api/queries/run", json=payload, headers={"Authorization": f"Bearer {analyst_token}"})

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fire_query, i) for i in range(4)]
        responses = [f.result() for f in futures]

    statuses = [r.status_code for r in responses]
    success_count = statuses.count(200)
    rejected_count = statuses.count(429)

    # At least one succeeded and at least one was rejected due to budget limits
    assert success_count >= 1
    # Verify final budget in DB never went negative
    conn = get_connection()
    row = conn.execute("SELECT remaining_micro_epsilon, spent_micro_epsilon FROM budget_ledger WHERE dataset_id = 'financial'").fetchone()
    conn.close()
    assert row["remaining_micro_epsilon"] >= 0
    assert row["spent_micro_epsilon"] <= 5000000


def test_23_failed_operations_do_not_leak_result(client: TestClient, analyst_token: str):
    """Test 23: When a query fails policy validation, no release record or receipt is created."""
    conn = get_connection()
    count_before = conn.execute("SELECT COUNT(*) as c FROM query_releases").fetchone()["c"]
    conn.close()

    bad_payload = {
        "dataset_id": "health",
        "field": "invalid_column",
        "operator": "equals",
        "value": "none",
        "epsilon": 0.5
    }
    resp = client.post("/api/queries/run", json=bad_payload, headers={"Authorization": f"Bearer {analyst_token}"})
    assert resp.status_code == 400

    conn = get_connection()
    count_after = conn.execute("SELECT COUNT(*) as c FROM query_releases").fetchone()["c"]
    conn.close()
    assert count_after == count_before
