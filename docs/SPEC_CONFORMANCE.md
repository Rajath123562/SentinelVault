# HOTFIX — Specification Conformance Matrix

**Project Name**: HOTFIX Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Current Phase**: Phase 1 Foundation  
**Version**: 1.0.0

---

## 1. Specification Conformance Matrix

This matrix tracks conformance between high-level Track 4 requirements, implemented architectural components, and automated test proof:

| Spec Item / Clause | Source | Implemented Component | Verifying Test / Evidence | Actual Test Status | Unresolved Dependency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P1-CONF-01**: System Startup & Liveness | Phase 1 Prompt Sec. 4.G | `backend/app/main.py`, `app/api/routes/system.py` | `test_b01_application_startup`, `test_b02_health_endpoint` | **PASS** | None |
| **P1-CONF-02**: Application Readiness vs Privacy Readiness | Phase 1 Prompt Sec. 4.G | `backend/app/api/routes/system.py` | `test_b03_readiness_distinguishes_app_from_privacy_readiness` | **PASS** | None |
| **P1-CONF-03**: System Status Reporting | Phase 1 Prompt Sec. 4.G | `backend/app/schemas/system.py`, `app/api/routes/system.py` | `test_b04_system_status_schema`, `test_b11_api_contract_consistency` | **PASS** | None |
| **P1-CONF-04**: Configuration Validation | Phase 1 Prompt Sec. 4.E | `backend/app/core/config.py` | `test_b05_valid_configuration_accepted`, `test_b05_malformed_configuration_rejected`, `test_b05_invalid_port_rejected` | **PASS** | None |
| **P1-CONF-05**: Privacy Release Default Disabled | Phase 1 Prompt Sec. 4.E | `config/app.yaml`, `config/spec.yaml`, `backend/app/core/config.py` | `test_b06_privacy_release_disabled_by_default` | **PASS** | None |
| **P1-CONF-06**: Missing Specification Fail-Closed | Phase 1 Prompt Sec. 4.E | `backend/app/core/config.py` | `test_b07_missing_or_unconfigured_spec_prevents_release` | **PASS** | Official Track 4 Accounting Spec |
| **P1-CONF-07**: Invalid Specification Rejected | Phase 1 Prompt Sec. 4.E | `backend/app/core/config.py` | `test_b08_invalid_specification_rejected_or_fails_closed` | **PASS** | Official Track 4 Accounting Spec |
| **P1-CONF-08**: Error Safety & Non-Leakage | Phase 1 Prompt Sec. 4.I | `backend/app/main.py` exception handlers | `test_b09_unhandled_exception_does_not_leak_traceback_or_secrets`, `test_b09_validation_error_is_sanitized` | **PASS** | None |
| **P1-CONF-09**: No False Feature Claims | Phase 1 Prompt Sec. 3.R2 | `backend/app/api/routes/system.py` | `test_b10_no_false_feature_claims` | **PASS** | None |
| **P1-CONF-10**: Release Guard Route Rejection | Phase 1 Prompt Sec. 3.R4 | `backend/app/main.py` route `/api/v1/query/release` | `test_b12_fail_closed_release_guard_route` | **PASS** | Phase 3 DP Engine |
| **P1-CONF-11**: Frontend Live Status Rendering | Phase 1 Prompt Sec. 4.H | `frontend/src/App.tsx`, `frontend/src/services/api.ts` | Vitest `tests/App.test.tsx` (Tests 1 & 2) | **PASS** | None |
| **P1-CONF-12**: Frontend Offline & Timeout Handling | Phase 1 Prompt Sec. 4.H | `frontend/src/services/api.ts`, `frontend/src/components/ConnectionAlert.tsx` | Vitest `tests/App.test.tsx` (Tests 3 & 4) | **PASS** | None |
| **P1-CONF-13**: Frontend Fail-Closed Release Display | Phase 1 Prompt Sec. 4.H | `frontend/src/components/StatusBanner.tsx` | Vitest `tests/App.test.tsx` (Test 5) | **PASS** | None |
| **P1-CONF-14**: Cumulative Epsilon Mission Cap ($\le 5.0$) | Track 4 Competition Rule | `config/spec.yaml` (`cap_epsilon: 5.0`) | `backend/app/core/config.py` validator | **PASS** | Formal accounting engine (Phase 3) |

---

## 2. Unresolved Specification Items

The official competition specification for Track 4 has not yet been placed in the repository. The following items remain deferred until official confirmation:
* Official specification version and URI.
* Unit of privacy (patient, customer, transaction).
* Adjacency definition (unbounded vs bounded).
* Global clipping bounds and sensitivity calculation rules.
* Official accounting algorithm (PLD / RDP / Moments Accountant).

