# HOTFIX — Requirements Traceability Matrix (RTM)

**Project Name**: HOTFIX Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Current Phase**: Phase 1 Foundation  
**Version**: 1.0.0

---

## 1. Traceability Overview

This document preserves the original project proposal contract and maps every functional and non-functional requirement to target architectural modules, implementation phases, verification methods, and current empirical statuses.

### Standardized Status Definitions:
* **PLANNED**: Requirement is formally mapped and designed; implementation scheduled for a subsequent phase.
* **IN_PROGRESS**: Active development underway in the current phase.
* **IMPLEMENTED**: Code exists in repository and has passed initial unit checks.
* **VERIFIED**: Automated test or empirical terminal evidence confirms complete conformance with zero mocks.
* **BLOCKED**: Implementation blocked by external missing prerequisite (e.g., official specification or dataset).
* **NOT_APPLICABLE**: Formally excluded with justified rationale.

---

## 2. Requirements Traceability Table (R01 – R21)

| Req ID | Original Proposal Intention | Planned Architecture Module | Target Phase | Verification Method | Current Status | Notes / Phase 1 Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **R01** | User authentication through secure login credentials. | `backend/app/api/auth.py`, `backend/app/services/auth.py` | Phase 2 | Automated unit tests simulating valid/invalid credentials, password hashing tests (Argon2/bcrypt). | `PLANNED` | Not implemented in Phase 1. API status honestly reports auth as PLANNED. |
| **R02** | Temporary lockout after five consecutive failed login attempts. | `backend/app/services/auth_lockout.py` | Phase 2 | Automated test executing 5 sequential invalid attempts verifying 429/423 lockout response. | `PLANNED` | Contract preserved for Phase 2 auth module. |
| **R03** | Role-based access control (RBAC) granting privileges based on user role. | `backend/app/core/rbac.py` | Phase 2 | Role permission matrix tests verifying Analyst vs Admin route restrictions. | `PLANNED` | Scheduled for Phase 2. |
| **R04** | Dataset analysis and verification upon ingestion. | `backend/app/services/dataset_validator.py` | Phase 2 | Schema conformance and checksum verification tests on synthetic datasets. | `PLANNED` | Official datasets not present in workspace; marked PLANNED. |
| **R05** | Sensitive-information detection and classification. | `backend/app/services/pii_classifier.py` | Phase 2 | Classification tests asserting direct/quasi-identifier detection on schema definitions. | `PLANNED` | Scheduled for Phase 2 dataset ingestion pipeline. |
| **R06** | Data-quality and anomaly checks. | `backend/app/services/anomaly_detector.py` | Phase 2 | Outlier, null-rate, and distribution shift detection unit tests. | `PLANNED` | Scheduled for Phase 2. |
| **R07** | Restriction of raw-record access for ordinary analysts. | `backend/app/core/release_guard.py` | Phase 1 & 2 | Route guard test `test_b12_fail_closed_release_guard_route` verifying HTTP 403 on raw release attempts. | `VERIFIED` | Fail-closed guard route `/api/v1/query/release` implemented and verified in Phase 1. |
| **R08** | Differential privacy mechanisms preserving privacy bounds. | `backend/app/engine/dp_mechanisms.py` | Phase 3 | Mathematical noise distribution validation tests (Laplace/Gaussian) and empirical variance checks. | `PLANNED` | Differential privacy engine explicitly disabled in Phase 1. |
| **R09** | Cumulative privacy-budget enforcement (cap $\epsilon \le 5.0$). | `backend/app/engine/budget_ledger.py` | Phase 3 | Sequential query simulation verifying execution rejection when remaining budget is insufficient. | `PLANNED` | Target constraint $\epsilon \le 5.0$ documented in `config/spec.yaml`. |
| **R10** | Re-identification and membership-inference attack evaluation. | `backend/app/services/risk_evaluator.py` | Phase 4 | Automated test against evaluation harness computing empirical privacy leakage metrics. | `PLANNED` | Official evaluation harness not yet available in workspace. |
| **R11** | Threat-level display and risk-based query restrictions. | `backend/app/services/risk_policy.py`, `frontend/src/components/RiskBanner.tsx` | Phase 4 | End-to-end test asserting query rejection when threat score exceeds threshold. | `PLANNED` | Risk UI elements omitted from Phase 1 frontend to prevent simulated visuals. |
| **R12** | Confidence or uncertainty reporting where mathematically justified. | `backend/app/engine/uncertainty.py` | Phase 3 | Verification of analytic confidence interval bounds returned with DP results. | `PLANNED` | Scheduled for Phase 3 alongside DP mechanisms. |
| **R13** | Utility comparison with prescribed non-private baseline. | `backend/app/services/utility_benchmark.py` | Phase 4 | Mean squared error (MSE) and relative error calculations comparing private to exact aggregates. | `PLANNED` | Requires official baseline queries and datasets. |
| **R14** | Prediction task evaluation, if required by official resources. | `backend/app/services/prediction_evaluator.py` | Phase 4 | Model accuracy, F1 score, or AUC verification on private synthetic training data. | `PLANNED` | Awaiting confirmation from Track 4 official resources. |
| **R15** | Verifiable Privacy Receipts issued for every released query. | `backend/app/services/receipt_generator.py` | Phase 5 | Cryptographic receipt signature validation test and JSON payload schema check. | `PLANNED` | Scheduled for Phase 5. |
| **R16** | Signed, tamper-evident audit records. | `backend/app/services/audit_logger.py` | Phase 5 | Merkle-tree or hash-chain integrity verification test on audit log entries. | `PLANNED` | Scheduled for Phase 5. |
| **R17** | Correct privacy accounting across repeated and related queries. | `backend/app/engine/privacy_accountant.py` | Phase 3 | Multi-query composition test verifying cumulative budget subtraction under official accounting method. | `PLANNED` | Awaiting official Track 4 accounting specification. |
| **R18** | JSON and human-readable accountability reports. | `backend/app/services/report_exporter.py` | Phase 5 | Export test verifying structured JSON schema and markdown/PDF report generation. | `PLANNED` | Scheduled for Phase 5. |
| **R19** | React/TypeScript frontend interface. | `frontend/` (Vite, React 19, TypeScript) | Phase 1 | Vitest test suite (`tests/App.test.tsx`), TypeScript type check (`tsc --noEmit`), and Vite build. | `VERIFIED` | 6/6 frontend unit tests pass; production build succeeds; live communication verified. |
| **R20** | FastAPI backend server architecture. | `backend/app/main.py`, `app/api/routes/` | Phase 1 | Pytest test suite (`tests/test_health.py`, `test_system_status.py`, etc.), HTTP smoke test. | `VERIFIED` | 16/16 backend tests pass; `/health`, `/ready`, `/api/system/status` verified live. |
| **R21** | Database support (SQLite for local dev, PostgreSQL for production). | `backend/app/core/config.py` (database block) | Phase 1 & 2 | Configuration validation test asserting dialect/URL parsing; Phase 2 connection test. | `IMPLEMENTED` | Configuration schema defines SQLite/PostgreSQL fields (`config/app.yaml`). Persistent store deferred to Phase 2. |

---

## 3. Phase 1 Verification Summary

* **Total Requirements Defined**: 21
* **Phase 1 Verified Requirements**: **R07**, **R19**, **R20** (All backed by raw automated test outputs)
* **Phase 1 Implemented Configuration Requirements**: **R21** (Database configuration schema validated)
* **Planned for Subsequent Phases**: **R01–R06**, **R08–R18** (Formally mapped and scheduled)
* **Orphan Requirements**: **0** (All proposal items have assigned architectural homes)
