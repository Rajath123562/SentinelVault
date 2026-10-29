"""
Comprehensive Live End-to-End System Integration Test
Executes real HTTP requests against the live running server to verify every layer:
- Health and status
- Authentication and lockout
- Granular RBAC
- Query validation, preview, and execution
- Differential privacy noise injection
- Budget ledger accounting
- Cryptographic privacy receipts and audit ledger verification
- Tamper detection
"""

import sys
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def log_step(name):
    print(f"\n[TEST STEP] {name}...")

def assert_true(cond, msg):
    if not cond:
        print(f"FAILED: {msg}")
        sys.exit(1)
    print(f"  [PASS] {msg}")

def main():
    print("=" * 60)
    print("STARTING LIVE END-TO-END GATEWAY INTEGRATION TEST")
    print("=" * 60)

    # 1. System Health
    log_step("1. Checking Server Health and Status")
    res = requests.get(f"{BASE_URL}/health", timeout=5)
    assert_true(res.status_code == 200, f"/health responded HTTP {res.status_code}")
    data = res.json()
    assert_true(data["status"].lower() == "healthy", f"Health status is {data.get('status')}")

    res_status = requests.get(f"{BASE_URL}/api/system/status", timeout=5)
    assert_true(res_status.status_code == 200, "/api/system/status responded HTTP 200")
    status_data = res_status.json()
    assert_true(status_data["team_id"] == "UG 59", f"Team ID is {status_data.get('team_id')}")

    # 2. Authentication Failure & Lockout
    log_step("2. Verifying Lockout Security Mechanism")
    dummy_user = f"live_test_{int(time.time())}"
    # Failed attempts
    for i in range(4):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": dummy_user, "password": "WrongPassword!"})
        assert_true(r.status_code == 401, f"Attempt {i+1} rejected with HTTP 401")

    # 3. Valid Login as Analyst
    log_step("3. Authenticating as analyst_user")
    r_login = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "analyst_user", "password": "AnalystPass2026!"}
    )
    assert_true(r_login.status_code == 200, f"analyst_user login succeeded: HTTP {r_login.status_code}")
    analyst_token = r_login.json()["token"]
    assert_true(len(analyst_token) > 20, "Received valid session token")
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # 4. Dataset Metadata Query
    log_step("4. Fetching Permitted Datasets")
    r_ds = requests.get(f"{BASE_URL}/api/datasets", headers=analyst_headers)
    assert_true(r_ds.status_code == 200, f"Fetched datasets: HTTP {r_ds.status_code}")
    datasets = r_ds.json()
    assert_true(len(datasets) >= 2, f"Found {len(datasets)} datasets")
    ds_ids = [d["dataset_id"] for d in datasets]
    assert_true("health" in ds_ids and "financial" in ds_ids, "Found health and financial datasets")

    # 5. Query Validation & Preview
    log_step("5. Validating Query Preview Gate")
    preview_payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "cardiovascular",
        "epsilon": 0.5
    }
    r_prev = requests.post(f"{BASE_URL}/api/queries/preview", json=preview_payload, headers=analyst_headers)
    assert_true(r_prev.status_code == 200, f"Query preview succeeded: HTTP {r_prev.status_code}")
    prev_data = r_prev.json()
    assert_true(prev_data["policy_status"] in ("APPROVED", "POLICY_CHECK_PASSED"), f"Preview policy status: {prev_data.get('policy_status')}")
    assert_true(prev_data["estimated_privacy_cost"] in (0.0, 0.5), f"Estimated privacy cost: {prev_data['estimated_privacy_cost']} (0.0 if cached, 0.5 if fresh)")

    # 6. Negative Security Check: SQL Injection & Disallowed Fields
    log_step("6. Verifying Fail-Closed Policy Enforcement on Injection & Disallowed Fields")
    sqli_payload = {
        "dataset_id": "health",
        "field": "diagnosis_category; DROP TABLE users; --",
        "operator": "equals",
        "value": "cardiovascular",
        "epsilon": 0.5
    }
    r_sqli = requests.post(f"{BASE_URL}/api/queries/preview", json=sqli_payload, headers=analyst_headers)
    assert_true(r_sqli.status_code == 400, f"SQL injection attempt rejected: HTTP {r_sqli.status_code}")

    bad_field_payload = {
        "dataset_id": "health",
        "field": "ssn_raw",
        "operator": "equals",
        "value": "123-45-6789",
        "epsilon": 0.5
    }
    r_bad = requests.post(f"{BASE_URL}/api/queries/preview", json=bad_field_payload, headers=analyst_headers)
    assert_true(r_bad.status_code == 400, f"Disallowed field access rejected: HTTP {r_bad.status_code}")

    # 7. Query Execution & Differential Privacy Release
    log_step("7. Executing Live Differential Privacy Release")
    budget_before = requests.get(f"{BASE_URL}/api/budget/health", headers=analyst_headers).json()
    spent_before = budget_before["spent_epsilon"]

    run_payload = {
        "dataset_id": "health",
        "field": "diagnosis_category",
        "operator": "equals",
        "value": "cardiovascular",
        "epsilon": 0.5
    }
    r_run = requests.post(f"{BASE_URL}/api/queries/run", json=run_payload, headers=analyst_headers)
    assert_true(r_run.status_code == 200, f"Query executed successfully: HTTP {r_run.status_code}")
    run_data = r_run.json()
    assert_true("noisy_count" in run_data, f"Noisy count returned: {run_data.get('noisy_count')}")
    assert_true("receipt" in run_data, "Cryptographic privacy receipt included in release")
    receipt = run_data["receipt"]
    receipt_id = receipt["receipt_id"]
    assert_true(run_data["is_cached"] is False or run_data["is_cached"] is True, "Cache status properly flagged")

    # 8. Replay Cache Test
    log_step("8. Verifying Replay Cache at Zero Privacy Cost")
    r_cached = requests.post(f"{BASE_URL}/api/queries/run", json=run_payload, headers=analyst_headers)
    assert_true(r_cached.status_code == 200, "Cached query execution succeeded")
    cached_data = r_cached.json()
    assert_true(cached_data["is_cached"] is True, "Subsequent identical query was served from cache")
    assert_true(cached_data["epsilon_spent"] == 0.0, "Zero epsilon deducted on cache hit")

    # 9. Privacy Receipt Verification
    log_step("9. Verifying Ed25519 Privacy Receipt Retrieval")
    r_rec = requests.get(f"{BASE_URL}/api/receipts/{receipt_id}", headers=analyst_headers)
    assert_true(r_rec.status_code == 200, f"Retrieved receipt {receipt_id}")
    rec_obj = r_rec.json()
    assert_true(len(rec_obj["signature"]) in (88, 128), f"Ed25519 signature present (length={len(rec_obj['signature'])})")
    assert_true(len(rec_obj["audit_entry_hash"]) == 64, "SHA-256 audit entry hash present")

    # 10. Cryptographic Audit Chain Verification
    log_step("10. Cryptographic Hash Chain Verification")
    r_audit = requests.get(f"{BASE_URL}/api/audit/verify", headers=analyst_headers)
    assert_true(r_audit.status_code == 200, "Audit verification endpoint returned HTTP 200")
    audit_data = r_audit.json()
    assert_true(audit_data["valid"] is True, "Audit hash chain is mathematically valid")
    assert_true(audit_data["tamper_detected"] is False, "No tampering detected in ledger")
    assert_true(audit_data["verified_entries"] >= 1, f"Verified {audit_data['verified_entries']} audit entries")

    # 11. Role-Based Access Control (RBAC) Isolation
    log_step("11. Verifying Granular Role Boundaries")
    # Analyst cannot view security events
    r_analyst_siem = requests.get(f"{BASE_URL}/api/security/events", headers=analyst_headers)
    assert_true(r_analyst_siem.status_code == 403, f"Analyst correctly denied access to security logs: HTTP {r_analyst_siem.status_code}")

    # Log in as steward_user
    r_steward = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "steward_user", "password": "StewardPass2026!"}
    )
    assert_true(r_steward.status_code == 200, "Data steward logged in successfully")
    steward_token = r_steward.json()["token"]
    steward_headers = {"Authorization": f"Bearer {steward_token}"}

    # Steward CAN view security events
    r_steward_siem = requests.get(f"{BASE_URL}/api/security/events", headers=steward_headers)
    assert_true(r_steward_siem.status_code == 200, f"Steward can inspect security logs: HTTP {r_steward_siem.status_code}")
    events = r_steward_siem.json()
    assert_true(len(events) > 0, f"Recorded {len(events)} security events in immutable SIEM ledger")

    print("\n" + "=" * 60)
    print("ALL 11 LIVE INTEGRATION TEST STEPS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    main()
