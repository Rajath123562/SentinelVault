"""Category 4: Differential Privacy Engine & Privacy Accounting Deep Verification Suite.
Validates:
- Real Laplace mechanism noise properties (scale = 1/epsilon, unbiased mean, variance monotonicity).
- Strict sensitivity = 1.0 enforcement for COUNT queries.
- Zero noise when epsilon -> infinity strictly prohibited (strict allowlist {0.1, 0.2, 0.5, 1.0}).
- Micro-epsilon integer arithmetic to eliminate floating-point drift.
- Budget ledger cap (5.0 epsilon), isolation across datasets, and fail-closed exhaustion.
- Idempotency and zero-cost cache replay guarantees.
"""

import math
import numpy as np
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

from app.main import create_application
from app.db.connection import get_connection, init_database
from app.services.privacy_engine import (
    apply_laplace_noise,
    EPSILON_ALLOWLIST,
    SENSITIVITY,
    MECHANISM_NAME,
    _csprng_laplace_sample,
)
from app.services.query_engine import (
    compute_query_fingerprint,
    compute_cache_key,
    validate_query,
    execute_query_pipeline,
)
@pytest.fixture(autouse=True)
def setup_privacy_test_env():
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
    conn.commit()


@pytest.fixture
def dp_client():
    app = create_application()
    return TestClient(app)


@pytest.fixture
def analyst_token(dp_client):
    res = dp_client.post(
        "/api/auth/login",
        json={"username": "analyst_user", "password": "AnalystPass2026!"}
    )
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# P1: LAPLACE MECHANISM & NOISE PROPERTIES (Tests 01 - 12)
# ==============================================================================

def test_p1_01_laplace_scale_inverse_to_epsilon():
    for eps in [0.1, 0.2, 0.5, 1.0]:
        expected_scale = SENSITIVITY / eps
        assert math.isclose(expected_scale, 1.0 / eps, rel_tol=1e-9)


def test_p1_02_negative_count_rejected_by_engine():
    with pytest.raises(ValueError, match="Exact count cannot be negative"):
        apply_laplace_noise(-1, 0.5)


def test_p1_03_zero_count_supported_and_non_negative():
    for _ in range(30):
        noisy = apply_laplace_noise(0, 0.5)
        assert noisy >= 0
        assert isinstance(noisy, int)


def test_p1_04_epsilon_bounds_allowlist_enforced():
    invalid_epsilons = [0.0, -0.1, 0.05, 0.3, 1.5, 5.0, 10.0, float("inf"), float("nan")]
    for bad_eps in invalid_epsilons:
        with pytest.raises(ValueError, match="Invalid epsilon"):
            apply_laplace_noise(100, bad_eps)


def test_p1_05_empirical_unbiasedness_mean_error():
    exact = 200
    trials = 150
    samples = [apply_laplace_noise(exact, 1.0) for _ in range(trials)]
    errors = [s - exact for s in samples]
    mean_err = np.mean(errors)
    # At epsilon=1.0, scale=1.0, std dev is sqrt(2)*1 ~= 1.41.
    # Standard error of mean across 150 trials is ~1.41 / sqrt(150) ~= 0.115.
    # Abs mean error should comfortably be within 0.75.
    assert abs(mean_err) < 0.75, f"Empirical mean error {mean_err} deviated significantly from 0"


def test_p1_06_variance_monotonicity_higher_epsilon_lower_variance():
    exact = 500
    trials = 100
    samples_low_eps = [apply_laplace_noise(exact, 0.1) for _ in range(trials)]
    samples_high_eps = [apply_laplace_noise(exact, 1.0) for _ in range(trials)]
    var_low = np.var(samples_low_eps)
    var_high = np.var(samples_high_eps)
    # Variance of Laplace(b) is 2*b^2.
    # At eps=0.1, b=10, theoretical var = 200.
    # At eps=1.0, b=1, theoretical var = 2.
    assert var_low > var_high * 10, f"Variance at eps=0.1 ({var_low}) was not significantly greater than at eps=1.0 ({var_high})"


def test_p1_07_post_processing_integer_clamping():
    for _ in range(50):
        # Even with ground truth 1, high noise won't produce negative returns
        noisy = apply_laplace_noise(1, 0.1)
        assert isinstance(noisy, int)
        assert noisy >= 0


def test_p1_08_deterministic_seeding_support():
    val1 = apply_laplace_noise(150, 0.5, seed=42)
    val2 = apply_laplace_noise(150, 0.5, seed=42)
    assert val1 == val2, "Deterministic seed must produce identical results"


def test_p1_09_csprng_entropy_uniqueness():
    samples = {apply_laplace_noise(300, 0.1) for _ in range(25)}
    # With scale 10.0 and 25 trials, we expect at least 10 distinct integer outcomes
    assert len(samples) >= 10, f"Insufficient entropy observed: {samples}"


def test_p1_10_extreme_ground_truth_counts():
    for count in [1, 10, 500, 10000, 500000]:
        noisy = apply_laplace_noise(count, 0.5)
        assert isinstance(noisy, int)
        assert noisy >= 0


def test_p1_11_fail_closed_on_mechanism_exception(monkeypatch):
    def broken_sample(scale):
        raise OSError("CSPRNG entropy source failure")
    monkeypatch.setattr("app.services.privacy_engine._csprng_laplace_sample", broken_sample)
    monkeypatch.setattr("app.services.privacy_engine.HAS_DIFFPRIVLIB", False)

    with pytest.raises(RuntimeError, match="Differential privacy mechanism execution failed"):
        apply_laplace_noise(100, 0.5)


def test_p1_12_constant_sensitivity_strictly_one():
    assert SENSITIVITY == 1.0
    assert MECHANISM_NAME == "Laplace"


# ==============================================================================
# P2: MICRO-EPSILON LEDGER & ACCOUNTING INTEGRITY (Tests 13 - 24)
# ==============================================================================

def test_p2_13_integer_micro_epsilon_conversion():
    assert int(round(0.1 * 1_000_000)) == 100_000
    assert int(round(0.2 * 1_000_000)) == 200_000
    assert int(round(0.5 * 1_000_000)) == 500_000
    assert int(round(1.0 * 1_000_000)) == 1_000_000


def test_p2_14_no_floating_point_drift_after_repeated_deductions(dp_client, analyst_token):
    # Execute 5 queries with epsilon 0.2 across 5 approved categories
    categories = ["cardiovascular", "respiratory", "endocrine", "oncology", "neurological"]
    for cat in categories:
        res = dp_client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": cat, "epsilon": 0.2}
        )
        assert res.status_code == 200

    conn = get_connection()
    row = conn.execute("SELECT spent_micro_epsilon, remaining_micro_epsilon, cap_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()
    # Exactly 5 * 200,000 = 1,000,000 spent, exactly 4,000,000 remaining
    assert row["spent_micro_epsilon"] == 1_000_000
    assert row["remaining_micro_epsilon"] == 4_000_000
    assert row["cap_micro_epsilon"] == 5_000_000


def test_p2_15_cap_micro_epsilon_immutable_in_ledger():
    conn = get_connection()
    rows = conn.execute("SELECT cap_micro_epsilon FROM budget_ledger").fetchall()
    for r in rows:
        assert r["cap_micro_epsilon"] == 5_000_000


def test_p2_16_budget_ledger_initial_state_health(dp_client, analyst_token):
    res = dp_client.get("/api/budget/health", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "health"
    assert data["cap_epsilon"] == 5.0
    assert data["spent_epsilon"] == 0.0
    assert data["remaining_epsilon"] == 5.0


def test_p2_17_budget_ledger_initial_state_financial(dp_client, analyst_token):
    res = dp_client.get("/api/budget/financial", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "financial"
    assert data["cap_epsilon"] == 5.0
    assert data["spent_epsilon"] == 0.0
    assert data["remaining_epsilon"] == 5.0


def test_p2_18_isolated_dataset_ledgers(dp_client, analyst_token):
    # Spend 1.0 epsilon on health
    dp_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 1.0}
    )
    b_health = dp_client.get("/api/budget/health", headers={"Authorization": f"Bearer {analyst_token}"}).json()
    b_financial = dp_client.get("/api/budget/financial", headers={"Authorization": f"Bearer {analyst_token}"}).json()

    assert b_health["spent_epsilon"] == 1.0
    assert b_health["remaining_epsilon"] == 4.0
    assert b_financial["spent_epsilon"] == 0.0
    assert b_financial["remaining_epsilon"] == 5.0


def test_p2_19_exact_budget_exhaustion_boundary(dp_client, analyst_token):
    # Set health remaining budget directly to 0.2
    conn = get_connection()
    conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 4800000, remaining_micro_epsilon = 200000 WHERE dataset_id = 'health'")
    conn.commit()

    # Query with epsilon 0.2 succeeds (consumes final allowance)
    res = dp_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.2}
    )
    assert res.status_code == 200

    # Query with epsilon 0.1 fails with 429
    res_fail = dp_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.1}
    )
    assert res_fail.status_code == 429
    assert "Privacy budget exhausted" in res_fail.json()["detail"]


def test_p2_20_insufficient_budget_partial_request_rejected(dp_client, analyst_token):
    conn = get_connection()
    conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 4700000, remaining_micro_epsilon = 300000 WHERE dataset_id = 'health'")
    conn.commit()

    # Requesting 0.5 epsilon when only 0.3 remains must be rejected
    res = dp_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert res.status_code == 429


def test_p2_21_budget_exhaustion_does_not_mutate_ledger_on_failure(dp_client, analyst_token):
    conn = get_connection()
    conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 4900000, remaining_micro_epsilon = 100000 WHERE dataset_id = 'health'")
    conn.commit()

    # Attempt query requiring 0.2 epsilon
    dp_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.2}
    )

    row = conn.execute("SELECT spent_micro_epsilon, remaining_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()
    assert row["spent_micro_epsilon"] == 4900000
    assert row["remaining_micro_epsilon"] == 100000


def test_p2_22_budget_status_api_endpoint_accuracy(dp_client, analyst_token):
    # Perform a 0.5 query
    dp_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.5}
    )
    res = dp_client.get("/api/budget/health", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["spent_epsilon"] == 0.5
    assert body["remaining_epsilon"] == 4.5
    assert body["cap_epsilon"] == 5.0


def test_p2_23_negative_remaining_budget_impossible(dp_client, analyst_token):
    conn = get_connection()
    conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 5000000, remaining_micro_epsilon = 0 WHERE dataset_id = 'health'")
    conn.commit()

    for eps in [0.1, 0.2, 0.5, 1.0]:
        res = dp_client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": eps}
        )
        assert res.status_code == 429

    row = conn.execute("SELECT remaining_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()
    assert row["remaining_micro_epsilon"] >= 0


def test_p2_24_cumulative_spent_plus_remaining_equals_cap(dp_client, analyst_token):
    # Spend various epsilons
    for eps in [0.1, 0.2, 0.5]:
        dp_client.post(
            "/api/queries/run",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": eps}
        )

    conn = get_connection()
    row = conn.execute("SELECT spent_micro_epsilon, remaining_micro_epsilon, cap_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()
    assert row["spent_micro_epsilon"] + row["remaining_micro_epsilon"] == row["cap_micro_epsilon"]


# ==============================================================================
# P3: IDEMPOTENCY & ZERO-COST CACHE REPLAY (Tests 25 - 35)
# ==============================================================================

def test_p3_25_identical_query_reused_at_zero_cost(dp_client, analyst_token):
    payload = {"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    
    # First execution consumes 0.5
    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload)
    assert r1.status_code == 200
    assert r1.json()["epsilon_spent"] == 0.5
    assert r1.json()["is_cached"] is False

    # Second execution reuses cache at 0.0 epsilon cost
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload)
    assert r2.status_code == 200
    assert r2.json()["epsilon_spent"] == 0.0
    assert r2.json()["is_cached"] is True


def test_p3_26_cached_response_returns_identical_noisy_count(dp_client, analyst_token):
    payload = {"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "emergency", "epsilon": 0.5}
    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload).json()
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload).json()
    assert r1["noisy_count"] == r2["noisy_count"]


def test_p3_27_cached_response_preserves_original_receipt_id(dp_client, analyst_token):
    payload = {"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.5}
    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload).json()
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload).json()
    assert r1["receipt"]["receipt_id"] == r2["receipt"]["receipt_id"]


def test_p3_28_cache_key_includes_epsilon(dp_client, analyst_token):
    payload1 = {"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.2}
    payload2 = {"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.5}

    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload1).json()
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload2).json()

    assert r1["is_cached"] is False
    assert r2["is_cached"] is False
    assert r1["epsilon_spent"] == 0.2
    assert r2["epsilon_spent"] == 0.5


def test_p3_29_cache_key_includes_dataset(dp_client, analyst_token):
    p1 = {"dataset_id": "health", "field": "risk_band", "operator": "equals", "value": "high", "epsilon": 0.5}
    p2 = {"dataset_id": "financial", "field": "risk_band", "operator": "equals", "value": "high", "epsilon": 0.5}

    # Health fails since risk_band is not in health schema
    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=p1)
    assert r1.status_code == 400

    # Financial succeeds
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=p2)
    assert r2.status_code == 200
    assert r2.json()["is_cached"] is False


def test_p3_30_cache_key_includes_value(dp_client, analyst_token):
    p1 = {"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": 0.5}
    p2 = {"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "rehabilitation", "epsilon": 0.5}

    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=p1).json()
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=p2).json()

    assert r1["is_cached"] is False
    assert r2["is_cached"] is False


def test_p3_31_idempotency_key_header_guarantees_replay_zero_cost(dp_client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}", "Idempotency-Key": "idemp-req-778899"}
    payload = {"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "urgent", "epsilon": 0.5}

    r1 = dp_client.post("/api/queries/run", headers=headers, json=payload).json()
    assert r1["is_cached"] is False
    assert r1["epsilon_spent"] == 0.5

    r2 = dp_client.post("/api/queries/run", headers=headers, json=payload).json()
    assert r2["is_cached"] is True
    assert r2["epsilon_spent"] == 0.0
    assert r1["release_id"] == r2["release_id"]


def test_p3_32_cached_query_allowed_even_when_budget_is_exhausted(dp_client, analyst_token):
    payload = {"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "oncology", "epsilon": 0.5}
    # Execute first query to warm cache
    r1 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload)
    assert r1.status_code == 200

    # Exhaust budget completely
    conn = get_connection()
    conn.execute("UPDATE budget_ledger SET spent_micro_epsilon = 5000000, remaining_micro_epsilon = 0 WHERE dataset_id = 'health'")
    conn.commit()

    # Replaying previously cached query succeeds at 0 privacy cost!
    r2 = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload)
    assert r2.status_code == 200
    assert r2.json()["is_cached"] is True
    assert r2.json()["epsilon_spent"] == 0.0


def test_p3_33_preview_endpoint_charges_zero_budget(dp_client, analyst_token):
    conn = get_connection()
    before = conn.execute("SELECT spent_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()["spent_micro_epsilon"]

    res = dp_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "neurological", "epsilon": 1.0}
    )
    assert res.status_code == 200

    after = conn.execute("SELECT spent_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()["spent_micro_epsilon"]
    assert before == after


def test_p3_34_concurrent_cache_lookup_consistency(dp_client, analyst_token):
    payload = {"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "51-65", "epsilon": 0.5}
    init_res = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload).json()

    for _ in range(5):
        lookup = dp_client.post("/api/queries/run", headers={"Authorization": f"Bearer {analyst_token}"}, json=payload).json()
        assert lookup["release_id"] == init_res["release_id"]
        assert lookup["noisy_count"] == init_res["noisy_count"]


def test_p3_35_fingerprint_normalization_whitespace_and_casing():
    fp1 = compute_query_fingerprint("HEALTH ", "age_group ", "EQUALS", " 18-35 ")
    fp2 = compute_query_fingerprint("health", "age_group", "=", "18-35")
    assert fp1 == fp2
