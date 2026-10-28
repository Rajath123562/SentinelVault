# HOTFIX — System Architecture & Trust Boundary Specification

**System Name**: HOTFIX Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Current Phase**: Phase 1 Foundation  
**Version**: 1.0.0

---

## 1. System Architecture Overview

The HOTFIX system mediates access between untrusted analytical users (data scientists, healthcare analysts, financial auditors) and sensitive underlying synthetic datasets.

Ordinary analysts must never receive direct, unrestricted access to microdata rows. All analytical requests must transition through a multi-stage validation and defense pipeline:

```
[ Untrusted Client / Browser ]
           │
           ▼
[ Network Gateway / CORS Boundary ]
           │
           ▼
[ FastAPI Application Core ] ──────────┐
           │                           │
    (1) Authentication & RBAC          │
           │                           │
    (2) Query Validation & Syntax      │
           │                           │
    (3) Sensitivity & Contribution     │  Audit & Tamper-Evident Ledger
           │                           │  (Phase 5)
    (4) Privacy Budget Reservation     │
           │                           │
    (5) Differential Privacy Engine    │
           │                           │
    (6) Risk & Attack Gate             │
           │                           │
    (7) Verification & Budget Commit   │
           │                           │
    (8) Receipt & Release Formulation ─┘
           │
           ▼
[ Protected Analytical Result + Privacy Receipt ]
```

---

## 2. Component Implementation Timeline

The architecture spans five discrete phases. The table below clearly distinguishes Phase 1 foundations from future components:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HOTFIX ARCHITECTURAL MAP                              │
├────────────────────────────────────────────────────┬────────────────────────────┤
│ COMPONENT MODULE                                   │ IMPLEMENTATION STATUS      │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 1. Client Layer (React / TypeScript / Vite)       │ IMPLEMENTED (Phase 1)      │
│    - SystemStatusCard, StatusBanner, Metrics       │ Verified & Tested          │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 2. Backend Gateway (FastAPI / Starlette)          │ IMPLEMENTED (Phase 1)      │
│    - Core routing, CORS, Sanitized Exceptions     │ Verified & Tested          │
│    - Endpoints: /health, /ready, /api/system/status│ Verified & Tested          │
│    - Fail-Closed Release Guard Route               │ Verified & Tested          │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 3. Configuration & Specification Subsystem        │ IMPLEMENTED (Phase 1)      │
│    - app.yaml validation (ports, envs, logging)    │ Verified & Tested          │
│    - spec.yaml parsing & fail-closed release gate │ Verified & Tested          │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 4. Authentication & RBAC (R01, R02, R03)           │ PLANNED (Phase 2)          │
│    - JWT/Session, lockout after 5 failures         │ Future Pipeline Module     │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 5. Dataset Validation & Classification (R04, R05) │ PLANNED (Phase 2)          │
│    - Schema validation, PII/quasi-identifier tags │ Future Pipeline Module     │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 6. Restricted Query Parser (R07)                   │ PLANNED (Phase 2)          │
│    - Prohibits microdata SELECT * queries          │ Future Pipeline Module     │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 7. Differential Privacy Engine (R08, R12)          │ PLANNED (Phase 3)          │
│    - Laplace / Gaussian noise mechanisms           │ Awaiting Official Spec     │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 8. Privacy Budget Ledger (R09, R17)                │ PLANNED (Phase 3)          │
│    - Composition accountant, cumulative ε ≤ 5.0   │ Awaiting Official Spec     │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 9. Risk & Attack Evaluation Adapter (R10, R11)    │ PLANNED (Phase 4)          │
│    - Membership inference & re-identification check│ Awaiting Official Harness  │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 10. Utility Benchmark Evaluator (R13, R14)         │ PLANNED (Phase 4)          │
│    - MSE/error vs non-private baselines, ML tasks │ Awaiting Official Baseline │
├────────────────────────────────────────────────────┼────────────────────────────┤
│ 11. Signed Audit Records & Receipts (R15, R16, R18)│ PLANNED (Phase 5)          │
│    - Merkle-hash log chains, verifiable Receipts   │ Future Delivery Gate       │
└────────────────────────────────────────────────────┴────────────────────────────┘
```

---

## 3. Trust Boundary & Security Architecture

### 3.1 Non-Authoritative Client Policy
* The React frontend is completely **untrusted**.
* The browser never decides whether an analytical query is permitted, what noise is injected, how much privacy budget is deducted, or whether an attack risk threshold is exceeded.
* All access control, input validation, privacy accounting, and release gates are enforced **server-side** in Python/FastAPI.

### 3.2 Information Leakage Prevention
* Error responses from the backend never expose Python stack traces, internal database URLs, system directory paths, or unmasked exception strings.
* Standardized `ErrorResponse` schemas return high-level classifications (`error`, `detail`, `code`, `timestamp`) while sensitive diagnostics are isolated to server-side logs.

### 3.3 Fail-Closed Release Invariant
* During Phase 1, the differential privacy engine and official accounting specification are not present.
* The system enforces a strict fail-closed release invariant:
  * Any call to `/api/v1/query/release` is rejected with `HTTP 403 Forbidden` (`code: PRIVACY_RELEASE_DISABLED`).
  * `readiness.privacy_release_ready` is hard-locked to `False`.
  * Attempting to configure `privacy_release.enabled: true` in `app.yaml` while `spec.yaml` remains `NOT_CONFIGURED` raises a fatal configuration validation error on boot.

---

## 4. Data Flow in Phase 1

```
┌─────────────────────────────────┐
│     Client Browser (Vite/React) │
└────────────────┬────────────────┘
                 │
                 │ 1. GET /api/system/status
                 │    (Fetch system diagnostics)
                 ▼
┌─────────────────────────────────────────────────────────┐
│ FastAPI Application (backend/app/main.py)               │
│                                                         │
│   ├── CORS Middleware (Validates Origin)                │
│   ├── System Router (app/api/routes/system.py)          │
│   └── Settings Cache (app/core/config.py)               │
│         ├── Loads config/app.yaml                       │
│         ├── Loads config/spec.yaml                      │
│         └── Enforces Phase 1 Fail-Closed Invariant      │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ 2. JSON Response:
                 │    - application_health: "HEALTHY"
                 │    - configuration_valid: true
                 │    - privacy_releases_enabled: false
                 │    - official_spec_status: "NOT_CONFIGURED"
                 │    - 10 Capability Status entries
                 ▼
┌─────────────────────────────────┐
│ Rendered Status Dashboard:      │
│ "Foundation ready —             │
│  privacy releases disabled"     │
└─────────────────────────────────┘
```

This guarantees an honest, verified software baseline ready for incremental extension in Phase 2.

