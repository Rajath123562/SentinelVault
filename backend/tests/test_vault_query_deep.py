"""Category 3: Deep Verification Suite for Data Vault, Dataset Validation, and Query Security.

Covers 36 distinct test scenarios verifying data confinement, path traversal rejection,
strict query allowlist boundaries, SQL injection prevention, sensitive column classification,
and raw-row isolation.
"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_application
from app.services.query_engine import (
    validate_query,
    compute_query_fingerprint,
    compute_cache_key,
    get_dataset_metadata,
    list_available_datasets,
    PolicyViolationError,
)


@pytest.fixture(scope="module")
def vq_client():
    app = create_application()
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def analyst_token(vq_client):
    res = vq_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    assert res.status_code == 200
    return res.json()["token"]


# ==============================================================================
# V1: DATA CONFINEMENT & PATH TRAVERSAL DEFENSE (Tests 1 - 8)
# ==============================================================================

def test_v1_01_path_traversal_dot_dot_slash_rejected(vq_client, analyst_token):
    traversal_ids = [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "%2e%2e%2fetc%2fpasswd",
        "health/../../secret.json",
        "....//....//etc/shadow",
        "%00health.json",
    ]
    for tid in traversal_ids:
        res = vq_client.get(f"/api/budget/{tid}", headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code in [400, 404, 422], f"Path traversal '{tid}' was not safely rejected"


def test_v1_02_direct_database_file_access_not_served(vq_client):
    db_paths = [
        "/hotfix_mvp.db",
        "/test_isolated.db",
        "/backend/hotfix_mvp.db",
        "/data/health_records_demo.json",
        "/api/../hotfix_mvp.db",
    ]
    for path in db_paths:
        res = vq_client.get(path)
        assert res.status_code == 404, f"Database/internal file '{path}' must return 404"


def test_v1_03_unknown_dataset_id_rejected_with_400(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "classified_military_db", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.5}
    )
    assert res.status_code == 400
    assert "Unauthorized or unknown dataset" in res.json()["detail"]


def test_v1_04_dataset_metadata_returns_allowlist_without_records(vq_client, analyst_token):
    res = vq_client.get("/api/datasets", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    datasets = res.json()
    assert len(datasets) >= 2
    for ds in datasets:
        assert "records" not in ds
        assert "raw_data" not in ds
        assert "approved_fields" in ds
        assert ds["total_records"] > 0


def test_v1_05_metadata_privacy_unit_clearly_identified(vq_client, analyst_token):
    res = vq_client.get("/api/datasets", headers={"Authorization": f"Bearer {analyst_token}"})
    datasets = {d["dataset_id"]: d for d in res.json()}
    assert datasets["health"]["privacy_unit"] == "patient_id"
    assert datasets["financial"]["privacy_unit"] == "customer_id"


def test_v1_06_nonexistent_dataset_metadata_unit_helper():
    with pytest.raises(Exception):
        get_dataset_metadata("nonexistent_vault_99")


def test_v1_07_list_available_datasets_contains_official_demo_fixtures():
    ds_list = list_available_datasets()
    ids = [d["dataset_id"] for d in ds_list]
    assert "health" in ids
    assert "financial" in ids


def test_v1_08_dataset_description_is_descriptive_string():
    meta = get_dataset_metadata("health")
    assert isinstance(meta["description"], str)
    assert len(meta["description"]) > 10


# ==============================================================================
# V2: QUERY RESTRICTIONS & SQL INJECTION PREVENTION (Tests 9 - 22)
# ==============================================================================

def test_v2_09_sql_injection_union_select_rejected(vq_client, analyst_token):
    payloads = [
        "' UNION SELECT * FROM users --",
        "cardiovascular' OR '1'='1",
        "respiratory'; DROP TABLE users; --",
        "1' OR 1=1 --",
        "admin'--",
    ]
    for p in payloads:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": p, "epsilon": 0.5}
        )
        assert res.status_code == 400
        assert "not an approved category" in res.json()["detail"] or "invalid" in res.json()["detail"].lower()


def test_v2_10_arbitrary_sql_in_field_name_rejected(vq_client, analyst_token):
    injections = [
        "diagnosis_category, (SELECT password_hash FROM users LIMIT 1)",
        "patient_id; DROP TABLE budget_ledger;",
        "*",
        "COUNT(*)",
        "1=1",
    ]
    for inj in injections:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": inj, "operator": "equals", "value": "respiratory", "epsilon": 0.5}
        )
        assert res.status_code == 400
        assert "not in approved allowlist" in res.json()["detail"]


def test_v2_11_unsupported_operators_rejected(vq_client, analyst_token):
    disallowed_ops = ["!=", "<>", ">", "<", ">=", "<=", "LIKE", "ILIKE", "IN", "BETWEEN", "IS NULL", "MATCH"]
    for op in disallowed_ops:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": op, "value": "respiratory", "epsilon": 0.5}
        )
        assert res.status_code == 400
        assert "Unsupported operator" in res.json()["detail"]


def test_v2_12_operator_equals_string_and_symbol_both_accepted(vq_client, analyst_token):
    for op in ["equals", "=", "EQUALS", " = "]:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": op, "value": "respiratory", "epsilon": 0.5}
        )
        assert res.status_code == 200, f"Operator '{op}' should be normalized and accepted"


def test_v2_13_direct_identifier_field_cannot_be_queried(vq_client, analyst_token):
    # patient_id is the protected privacy unit, not an approved query category
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "patient_id", "operator": "equals", "value": "P-0001", "epsilon": 0.5}
    )
    assert res.status_code == 400
    assert "not in approved allowlist" in res.json()["detail"]


def test_v2_14_financial_account_id_direct_identifier_rejected(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "financial", "field": "account_id", "operator": "equals", "value": "ACC-1001", "epsilon": 0.5}
    )
    assert res.status_code == 400
    assert "not in approved allowlist" in res.json()["detail"]


def test_v2_15_record_id_cannot_be_queried(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "record_id", "operator": "equals", "value": "HREC-00001", "epsilon": 0.5}
    )
    assert res.status_code == 400
    assert "not in approved allowlist" in res.json()["detail"]


def test_v2_16_disallowed_epsilon_rejected(vq_client, analyst_token):
    invalid_epsilons = [0.0, -0.5, 0.05, 1.5, 2.0, 10.0, 999.0]
    for eps in invalid_epsilons:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": eps}
        )
        assert res.status_code == 400
        assert "not permitted" in res.json()["detail"]


def test_v2_17_permitted_epsilons_accepted(vq_client, analyst_token):
    for eps in [0.1, 0.2, 0.5, 1.0]:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": eps}
        )
        assert res.status_code == 200


def test_v2_18_case_insensitive_approved_value_accepted(vq_client, analyst_token):
    # 'Respiratory', 'RESPIRATORY', 'respiratory' should all match approved category
    for val in ["respiratory", "Respiratory", "RESPIRATORY"]:
        res = vq_client.post(
            "/api/queries/preview",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": val, "epsilon": 0.5}
        )
        assert res.status_code == 200


def test_v2_19_unapproved_category_value_rejected(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "zombie_virus_unknown", "epsilon": 0.5}
    )
    assert res.status_code == 400
    assert "not an approved category" in res.json()["detail"]


def test_v2_20_financial_dataset_approved_fields_and_values(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "financial", "field": "transaction_type", "operator": "equals", "value": "wire", "epsilon": 0.2}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "financial"
    assert data["estimated_privacy_cost"] == 0.2


def test_v2_21_financial_risk_level_field_query(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "financial", "field": "risk_band", "operator": "equals", "value": "high", "epsilon": 0.5}
    )
    assert res.status_code == 200


def test_v2_22_empty_string_value_rejected(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "", "epsilon": 0.5}
    )
    assert res.status_code == 400


# ==============================================================================
# V3: RAW ROW ISOLATION & DATA CONFINEMENT IN RELEASE (Tests 23 - 36)
# ==============================================================================

def test_v2_23_query_run_response_contains_no_raw_records(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "cardiovascular", "epsilon": 0.5}
    )
    assert res.status_code == 200
    data = res.json()
    assert "records" not in data
    assert "patient_id" not in data
    assert "noisy_count" in data
    assert isinstance(data["noisy_count"], int)


def test_v2_24_exact_count_never_returned_in_release_payload(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "admission_type", "operator": "equals", "value": "emergency", "epsilon": 0.5}
    )
    assert res.status_code == 200
    text = res.text
    assert "exact_count" not in text
    assert "true_count" not in text
    assert "ground_truth" not in text


def test_v2_25_preview_endpoint_does_not_leak_count(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "diagnosis_category", "operator": "equals", "value": "respiratory", "epsilon": 0.5}
    )
    assert res.status_code == 200
    data = res.json()
    assert "count" not in data
    assert "noisy_count" not in data
    assert "exact_count" not in data
    assert data["estimated_privacy_cost"] in [0.0, 0.5]


def test_v2_26_query_fingerprint_is_deterministic():
    fp1 = compute_query_fingerprint("health", "diagnosis_category", "equals", "respiratory")
    fp2 = compute_query_fingerprint("health", "diagnosis_category", "=", "respiratory")
    fp3 = compute_query_fingerprint("HEALTH", "DIAGNOSIS_CATEGORY", "EQUALS", "RESPIRATORY")
    assert fp1 == fp2 == fp3
    assert len(fp1) == 64


def test_v2_27_query_fingerprint_differentiates_values():
    fp1 = compute_query_fingerprint("health", "diagnosis_category", "equals", "respiratory")
    fp2 = compute_query_fingerprint("health", "diagnosis_category", "equals", "cardiovascular")
    assert fp1 != fp2


def test_v2_28_cache_key_includes_epsilon_and_mechanism():
    fp = compute_query_fingerprint("health", "diagnosis_category", "equals", "respiratory")
    ck1 = compute_cache_key("health", fp, 0.5, "Laplace")
    ck2 = compute_cache_key("health", fp, 1.0, "Laplace")
    assert ck1 != ck2
    assert "0.5000" in ck1
    assert "1.0000" in ck2


def test_v2_29_validate_query_helper_raises_on_invalid_field():
    with pytest.raises(PolicyViolationError):
        validate_query("health", "unapproved_field_x", "equals", "val", 0.5)


def test_v2_30_validate_query_helper_raises_on_invalid_operator():
    with pytest.raises(PolicyViolationError):
        validate_query("health", "diagnosis_category", "BETWEEN", "val", 0.5)


def test_v2_31_validate_query_helper_raises_on_invalid_value():
    with pytest.raises(PolicyViolationError):
        validate_query("health", "diagnosis_category", "equals", "bad_value", 0.5)


def test_v2_32_validate_query_helper_raises_on_invalid_epsilon():
    with pytest.raises(PolicyViolationError):
        validate_query("health", "diagnosis_category", "equals", "respiratory", 0.99)


def test_v2_33_validate_query_helper_succeeds_on_valid_inputs():
    meta = validate_query("health", "diagnosis_category", "equals", "respiratory", 0.5)
    assert meta["dataset_id"] == "health"


def test_v2_34_privacy_receipt_contains_no_sensitive_patient_identifiers(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "age_group", "operator": "equals", "value": "18-35", "epsilon": 0.5}
    )
    assert res.status_code == 200
    receipt = res.json()["receipt"]
    receipt_json = json.dumps(receipt)
    assert "P-" not in receipt_json
    assert "ACC-" not in receipt_json
    assert "C-" not in receipt_json


def test_v2_35_receipt_has_cryptographic_signature_and_hash(vq_client, analyst_token):
    res = vq_client.post(
        "/api/queries/run",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": 0.2}
    )
    assert res.status_code == 200
    receipt = res.json()["receipt"]
    assert "signature" in receipt
    assert len(receipt["signature"]) == 88  # Ed25519 signature base64 encoded
    assert "audit_entry_hash" in receipt
    assert len(receipt["audit_entry_hash"]) == 64  # SHA-256 hex


def test_v2_36_unauthenticated_request_to_queries_rejected(vq_client):
    res = vq_client.post(
        "/api/queries/run",
        json={"dataset_id": "health", "field": "discharge_status", "operator": "equals", "value": "routine", "epsilon": 0.2}
    )
    assert res.status_code == 401
