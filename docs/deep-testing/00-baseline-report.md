 # SentinelVault Deep Testing — Phase A: Baseline Report

**Product**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Team**: HOTFIX (Team ID: UG 59)  
**Track**: Track 4 — Privacy by Design  
**Date**: October 28, 2026  
**Document**: `docs/deep-testing/00-baseline-report.md`  
**Status**: **BASELINE ESTABLISHED & ISOLATED TEST ENVIRONMENT CONFIGURED**  

---

## 1. Workspace Inspection & Git Checkpoint

* **Repository Root**: `C:\Users\RAJATH U\Downloads\mit hackathon`
* **Branch**: `master`
* **Python Runtime**: Python 3.11.9 (pytest 9.1.1, hypothesis 6.169.1, fastapi, uvicorn)
* **Node Runtime**: Node.js v18+ (Vitest 2.1.9, React 18 / TypeScript 5)
* **Live Daemons Active**:
  * FastAPI Uvicorn Server: PID listening on `http://127.0.0.1:8000`
  * Vite Dev Server: PID listening on `http://localhost:5173`
* **Preservation Policy**: All existing modified files and untracked components are preserved without destructive Git commands.

---

## 2. Test Environment Isolation Protocol

In accordance with Phase A3 requirements:
1. **Demonstration Database**: `backend/hotfix_mvp.db` (Preserved intact for live demonstration and manual evaluation).
2. **Isolated Test Database**: `backend/test_isolated.db` (Configured via `HOTFIX_DB_PATH=test_isolated.db` in `backend/tests/conftest.py` and dynamic connection routing in `backend/app/db/connection.py`).
3. **Data Protection Invariant**: Automated test fixture teardowns (`DELETE FROM query_releases`, `DELETE FROM audit_log`, budget resets) execute **exclusively** against `test_isolated.db`. The production demonstration dataset is isolated from destructive test resets.
4. **Export Confinement**: `scripts/package_submission.py` excludes `test_isolated.db*`, `*.db-shm`, and `*.db-wal` from release packaging.

---

## 3. Baseline Test Suite Execution

The existing test suite was executed prior to deep testing modifications:

```
[Command 1]: $env:PYTHONPATH="backend"; python -m pytest backend/tests -v
Result: 94 passed, 2 warnings in 13.75s (Exit Code: 0)
Status: PASS

[Command 2]: npm test --prefix frontend
Result: 2 test files passed, 9 tests passed in 2.94s (Exit Code: 0)
Status: PASS

[Command 3]: npm run typecheck --prefix frontend
Result: 0 errors across 49 source modules (Exit Code: 0)
Status: PASS

[Command 4]: python scripts/live_gateway_test.py
Result: 11 / 11 live stages passed against running uvicorn server (Exit Code: 0)
Status: PASS
```

### Baseline Status by Capability Area

| Capability Area | Verification Evidence | Status |
| :--- | :--- | :--- |
| Application Lifecycle & Config | `test_config.py`, `test_health.py` | **PASS** |
| Zero-Trust Authentication | `test_mvp_auth.py`, `test_phase2_security.py` | **PASS** |
| 5-Attempt Lockout Defense | `test_phase2_security.py` (Cases 1–12) | **PASS** |
| Allowlist Query Grammar | `test_mvp_queries.py`, `test_phase3_vault.py` | **PASS** |
| Differential Privacy Engine | `test_mvp_privacy.py` | **PASS** |
| Shared Budget Ledger (ε ≤ 5.0) | `test_mvp_privacy.py`, `connection.py` | **PASS** |
| Zero-Cost Cache & Idempotency | `test_mvp_privacy.py`, `live_gateway_test.py` | **PASS** |
| Ed25519 Cryptographic Receipts | `test_mvp_audit.py` | **PASS** |
| SHA-256 Hash Chain Integrity | `test_mvp_audit.py`, `crypto_audit.py` | **PASS** |
| Security SIEM Events & Alerts | `test_phase2_security.py`, `api/routes/mvp.py`| **PASS** |
| 16-Screen Enterprise Frontend | `frontend/tests/*.test.tsx` (9 user journeys) | **PASS** |
| Official Track 4 Spec Conformance| External Competition Harness | **NOT IMPLEMENTED** (Demo accounting active) |
| Synthetic Adversary Pentesting | External Adversary Benchmark | **NOT IMPLEMENTED** (Honest disclosure) |
