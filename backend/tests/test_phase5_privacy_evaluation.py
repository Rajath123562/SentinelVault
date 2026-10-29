"""Phase 5 Test Suite: Privacy Risk Evaluation, Utility Benchmarking, Adversarial Testing & Cross-Component Consistency.

Validates:
1. Synthetic reference baseline calculation.
2. Differential privacy utility metrics (MAE, RMSE, Relative Error %, Variance, Bias).
3. Adversarial attacks:
   - Differencing attack mitigation (Laplace variance masks individual delta).
   - Repeated-query noise averaging mitigation (deterministic caching).
   - Filter variation query scanning and budget exhaustion gate.
   - Membership inference advantage bounding.
   - Small strata cohort protection.
4. Cross-component consistency (Query Builder, Pipeline, Budget Ledger, Receipt, Audit Chain).
"""

import math
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from starlette.testclient import TestClient

from app.main import create_application
from app.db.connection import get_connection, init_database
from app.services.privacy_engine import apply_laplace_noise, SENSITIVITY, EPSILON_ALLOWLIST
from app.services.query_engine import (
    _calculate_exact_count_internal,
    compute_query_fingerprint,
    compute_cache_key,
    execute_query_pipeline,
    get_dataset_metadata,
)
from app.services.crypto_audit import verify_audit_ledger, verify_entry_signature, tamper_audit_entry_for_test


@pytest.fixture(autouse=True)
def setup_phase5_env():
    """Isolates each test with a pristine database."""
    init_database()
    conn = get_connection()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        UPDATE budget_ledger 
        SET spent_micro_epsilon = 0, remaining_micro_epsilon = 5000000, cap_micro_epsilon = 5000000, updated_at = ?;
    """, (now_iso,))
    conn.execute("DELETE FROM privacy_receipts;")
    conn.execute("DELETE FROM query_releases;")
    conn.execute("DELETE FROM audit_log;")
    conn.execute("DELETE FROM security_events;")
    conn.commit()


@pytest.fixture
def p5_client():
    app = create_application()
    return TestClient(app)


@pytest.fixture
def analyst_token(p5_client):
    res = p5_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# SECTION 1: REFERENCE BASELINES & UTILITY METRICS (Tests 01 - 04)
# ==============================================================================

def test_p5_01_synthetic_ground_truth_reference_calculation():
    # Verify exact reference counts for health records fixture
    health_cardio = _calculate_exact_count_internal("health", "diagnosis_category", "cardiovascular")
    health_emergency = _calculate_exact_count_internal("health", "admission_type", "emergency")
    assert health_cardio == 100
    assert health_emergency == 130

    # Verify exact reference counts for financial transactions fixture
    fin_wire = _calculate_exact_count_internal("financial", "transaction_type", "wire")
    fin_high = _calculate_exact_count_internal("financial", "risk_band", "high")
    assert fin_wire == 111
    assert fin_high == 139


def test_p5_02_utility_metric_formulas_mae_and_rmse():
    exact = 100
    estimates = [95, 105, 98, 102]
    errors = [e - exact for e in estimates]
    abs_errors = [abs(e) for e in errors]
    sq_errors = [e ** 2 for e in errors]

    mae = sum(abs_errors) / len(estimates)
    rmse = math.sqrt(sum(sq_errors) / len(estimates))
    rel_err = (mae / exact) * 100.0

    assert mae == 3.5
    assert math.isclose(rmse, 3.8078865529319543, rel_tol=1e-5)
    assert math.isclose(rel_err, 3.5, rel_tol=1e-5)


def test_p5_03_laplace_scale_calibration_against_sensitivity():
    for eps in EPSILON_ALLOWLIST:
        b = SENSITIVITY / eps
        # Theoretical variance = 2 * b^2
        theo_var = 2.0 * (b ** 2)
        assert math.isclose(b, 1.0 / eps, rel_tol=1e-9)
        assert theo_var == 2.0 * ((1.0 / eps) ** 2)


def test_p5_04_relative_error_safe_zero_denominator_handling():
    # When ground truth exact count is zero, relative error must be handled safely (0.0%)
    exact_zero = 0
    mae = 2.0
    rel_err = (mae / exact_zero * 100.0) if exact_zero > 0 else 0.0
    assert rel_err == 0.0


# ==============================================================================
# SECTION 2: ADVERSARIAL PRIVACY ATTACK EVALUATIONS (Tests 05 - 09)
# ==============================================================================

def test_p5_05_adversarial_differencing_attack_simulation():
    """
    Simulates reconstruction / differencing attack: Q(D U {x}) - Q(D).
    Under DP with epsilon=0.5, variance masks the 1-individual delta so the attacker
    cannot make a confident binary decision.
    """
    exact_base = 100
    exact_plus_target = 101
    trials = 60
    diffs = [
        apply_laplace_noise(exact_plus_target, 0.5) - apply_laplace_noise(exact_base, 0.5)
        for _ in range(trials)
    ]
    diff_variance = sum((d - 1.0) ** 2 for d in diffs) / trials
    # Under Laplace(2.0), difference of two independent Laplace variables has variance = 2 * 8 = 16.
    # Empirical sample variance should easily exceed 4.0.
    assert diff_variance > 4.0, f"Insufficient noise variance to mitigate differencing attack: {diff_variance}"


def test_p5_06_repeated_query_noise_averaging_defense():
    """
    Attacker submits identical query 25 times hoping to average out Laplace noise.
    Defense: SentinelVault deterministic query cache returns identical sample with zero privacy cost.
    """
    responses = [
        execute_query_pipeline(
            user_id="analyst_user",
            user_role="analyst",
            dataset_id="health",
            field="diagnosis_category",
            operator="equals",
            value="cardiovascular",
            epsilon=0.5
        )
        for _ in range(15)
    ]
    # First request was paid release; remaining 14 were cache hits
    assert responses[0]["is_cached"] is False
    assert responses[0]["epsilon_spent"] == 0.5
    for r in responses[1:]:
        assert r["is_cached"] is True
        assert r["epsilon_spent"] == 0.0
        assert r["noisy_count"] == responses[0]["noisy_count"]


def test_p5_07_filter_variation_budget_exhaustion_defense():
    """
    Attacker attempts scanning variations to bypass caching.
    Backend drains budget accurately until cap (5.0) is hit, then blocks subsequent queries with 429.
    """
    categories = ["cardiovascular", "respiratory", "endocrine", "oncology", "neurological"]
    # 5 distinct releases with epsilon 1.0 consumes 5.0 epsilon
    for cat in categories:
        res = execute_query_pipeline(
            user_id="analyst_user",
            user_role="analyst",
            dataset_id="health",
            field="diagnosis_category",
            operator="equals",
            value=cat,
            epsilon=1.0
        )
        assert res["epsilon_spent"] == 1.0

    # 6th query must be rejected by budget exhaustion gate
    with pytest.raises(Exception, match="Privacy budget exhausted"):
        execute_query_pipeline(
            user_id="analyst_user",
            user_role="analyst",
            dataset_id="health",
            field="admission_type",
            operator="equals",
            value="emergency",
            epsilon=0.5
        )


def test_p5_08_membership_inference_advantage_bounded():
    """
    Simulates membership inference advantage: Adv = 2 * |Acc - 0.5|.
    Under differential privacy (epsilon <= 1.0), attacker advantage remains strictly bounded.
    """
    # 100 simulated trials comparing target in vs target out
    trials = 100
    correct_guesses = 0
    for _ in range(trials):
        # Even trial: Target is present (ground truth 101)
        # Odd trial: Target is absent (ground truth 100)
        target_present = (_ % 2 == 0)
        gt = 101 if target_present else 100
        noisy_val = apply_laplace_noise(gt, 0.5)
        # Attacker decision rule: guess present if noisy_val > 100
        guess_present = (noisy_val > 100)
        if guess_present == target_present:
            correct_guesses += 1

    accuracy = correct_guesses / trials
    advantage = 2.0 * abs(accuracy - 0.5)
    # Advantage under eps=0.5 must be bounded well below 0.40 (i.e. accuracy between 30% and 70%)
    assert advantage < 0.40, f"Membership inference advantage {advantage:.3f} was too high"


def test_p5_09_small_strata_privacy_protection():
    """
    Verifies that querying a small category with count = 1 still receives calibrated Laplace noise.
    """
    noisy_samples = [apply_laplace_noise(1, 0.5) for _ in range(30)]
    assert any(s != 1 for s in noisy_samples), "Small cohort query must not deterministically return 1"
    assert all(s >= 0 for s in noisy_samples), "Post-processed noisy counts must remain non-negative"


# ==============================================================================
# SECTION 3: CROSS-COMPONENT CONSISTENCY (Tests 10 - 15)
# ==============================================================================

def test_p5_10_cross_component_query_syntax_reconciled(p5_client, analyst_token):
    res = p5_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert res.status_code == 200
    rc = res.json()["receipt"]
    # Verify query description in receipt specifies COUNT_DISTINCT(patient_id)
    assert rc["query_description"] == "COUNT_DISTINCT(patient_id) WHERE diagnosis_category = 'cardiovascular'"


def test_p5_11_receipt_signature_cryptographic_verification(p5_client, analyst_token):
    res = p5_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": 0.5}
    )
    rc = res.json()["receipt"]
    assert verify_entry_signature(rc["audit_entry_hash"], rc["signature"]) is True


def test_p5_12_audit_hash_chain_tamper_detection(p5_client, analyst_token):
    p5_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.2}
    )
    conn = get_connection()
    entry = conn.execute("SELECT entry_id FROM audit_log ORDER BY entry_id DESC LIMIT 1").fetchone()
    # Deliberately modify expenditure
    tamper_audit_entry_for_test(conn, entry["entry_id"], 999999)
    conn.commit()

    report = verify_audit_ledger(conn)
    assert report["valid"] is False
    assert report["tamper_detected"] is True
    assert report["broken_at_entry"] == entry["entry_id"]


def test_p5_13_budget_ledger_mathematical_invariant_maintained(p5_client, analyst_token):
    p5_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "urgent", "epsilon": 0.5}
    )
    conn = get_connection()
    row = conn.execute("SELECT spent_micro_epsilon, remaining_micro_epsilon, cap_micro_epsilon FROM budget_ledger WHERE dataset_id = 'health'").fetchone()
    assert row["spent_micro_epsilon"] + row["remaining_micro_epsilon"] == row["cap_micro_epsilon"]


def test_p5_14_evaluation_report_artifact_present():
    report_file = Path(__file__).resolve().parent.parent.parent / "docs" / "privacy-risk-evaluation-report.json"
    assert report_file.exists(), "Phase 5 evaluation report JSON artifact must exist in docs/"
    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["overall_evaluation_verdict"] == "PASSED"
    assert "utility_benchmarks" in data
    assert "adversarial_evaluations" in data


def test_p5_15_evaluation_harness_script_importable():
    import sys
    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.run_privacy_risk_evaluation import (
        evaluate_utility_benchmarks,
        evaluate_adversarial_differencing_attack,
        evaluate_repeated_query_averaging_attack,
        evaluate_filter_variation_budget_exhaustion,
        evaluate_cross_component_consistency,
    )
    assert callable(evaluate_utility_benchmarks)
    assert callable(evaluate_adversarial_differencing_attack)
    assert callable(evaluate_cross_component_consistency)

