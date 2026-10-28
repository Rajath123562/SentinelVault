# HOTFIX — API Contracts & Endpoint Specifications

**Project Name**: HOTFIX Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Current Phase**: Phase 1 Foundation  
**Version**: 1.0.0

---

## 1. Phase 1 Implemented System Endpoints

### 1.1 Liveness Probe
* **Endpoint**: `GET /health`
* **Purpose**: Verifies that the FastAPI process is alive and capable of serving HTTP traffic.
* **Status Code**: `200 OK`
* **Response Headers**: `Content-Type: application/json`
* **Response Body**:
  ```json
  {
    "status": "healthy",
    "service": "hotfix-backend",
    "timestamp": "2026-10-28T11:00:00.000000Z"
  }
  ```
* **Security & Non-Leakage Guarantees**:
  * Does NOT expose database credentials, environment variables, or secret keys.
  * Does NOT claim that differential privacy or authentication engines are operational.

---

### 1.2 Readiness Probe
* **Endpoint**: `GET /ready`
* **Purpose**: Evaluates system readiness while strictly distinguishing application readiness from privacy release readiness.
* **Status Code**: `200 OK`
* **Response Body**:
  ```json
  {
    "status": "ready",
    "phase": "Phase 1",
    "application_initialized": true,
    "configuration_valid": true,
    "privacy_release_ready": false,
    "privacy_engine_implemented": false,
    "official_spec_status": "NOT_CONFIGURED",
    "evaluation_harness_status": "UNAVAILABLE",
    "release_disabled_reason": "Phase 1 foundation: Differential privacy engine and official accounting specification not yet configured"
  }
  ```
* **Security Invariant**:
  * `privacy_release_ready` is hard-locked to `false` during Phase 1.
  * Incomplete official specifications cannot silently enable releases.

---

### 1.3 System Status Payload
* **Endpoint**: `GET /api/system/status`
* **Purpose**: Supplies structured operational and capability status for frontend rendering and diagnostic tooling.
* **Status Code**: `200 OK`
* **Response Body**:
  ```json
  {
    "project_name": "HOTFIX Privacy-by-Design Analytics Gateway",
    "project_code": "HOTFIX",
    "team_id": "UG 59",
    "current_phase": "Phase 1",
    "application_health": "HEALTHY",
    "configuration_valid": true,
    "privacy_releases_enabled": false,
    "release_disabled_reason": "Phase 1 foundation: Differential privacy engine and official accounting specification not yet configured",
    "official_spec_status": "NOT_CONFIGURED",
    "official_harness_status": "NOT_INTEGRATED",
    "server_time": "2026-10-28T11:00:00.000000Z",
    "capabilities": [
      {
        "id": "CAP-01-FOUNDATION",
        "name": "Application Foundation & Lifecycle",
        "status": "IMPLEMENTED",
        "phase": "Phase 1",
        "description": "FastAPI application structure, routing, schemas, and lifecycle management."
      },
      {
        "id": "CAP-02-CONFIG-GATES",
        "name": "Configuration & Fail-Closed Privacy Gates",
        "status": "IMPLEMENTED",
        "phase": "Phase 1",
        "description": "Validated YAML configuration, environment overrides, and fail-closed release controls."
      },
      {
        "id": "CAP-03-AUTH-RBAC",
        "name": "Authentication & Role-Based Access Control",
        "status": "PLANNED",
        "phase": "Phase 2",
        "description": "Credential verification, temporary lockout after 5 failures, and role-based privilege checks."
      }
    ]
  }
  ```

---

### 1.4 Fail-Closed Release Route (Guard Route)
* **Endpoint**: `ALL /api/v1/query/release`
* **Purpose**: Prevents accidental or unauthorized release of analytical queries during Phase 1.
* **Status Code**: `403 Forbidden`
* **Response Body**:
  ```json
  {
    "error": "Privacy Release Disabled",
    "detail": "Privacy releases are strictly disabled in Phase 1. The differential privacy engine and official accounting specification have not been integrated.",
    "code": "PRIVACY_RELEASE_DISABLED",
    "timestamp": "2026-10-28T11:00:00.000000Z"
  }
  ```

---

## 2. Standardized Error Contract

All backend exceptions adhere to a standardized, sanitized payload:

```json
{
  "error": "Error Classification (e.g. HTTP Error, Validation Error, Internal Server Error)",
  "detail": "Sanitized human-readable explanation",
  "code": "Machine-readable status code or error code string",
  "timestamp": "ISO-8601 UTC timestamp"
}
```

* **No Stack Traces**: Handled and unhandled exceptions strip all Python internal tracebacks.
* **No Path Leaks**: Absolute system paths (e.g., `C:\Users\...`) are redacted from public responses.
* **No Secret Exposure**: Passwords, tokens, API keys, or database credentials are never reflected in error details.

---

## 3. Planned Future API Contracts (Phases 2 – 5)

The following endpoints represent future contracts designed for subsequent phases. In strict compliance with **Rule 2 (No fake functionality)**, these endpoints are NOT mocked or implemented prematurely in Phase 1:

| Target Endpoint | Method | Planned Phase | Target Purpose |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/login` | `POST` | Phase 2 | Authenticates user; enforces 5-attempt lockout (R01, R02). |
| `/api/v1/auth/logout` | `POST` | Phase 2 | Invalidates active user session token. |
| `/api/v1/datasets` | `GET` | Phase 2 | Returns metadata and schemas for validated datasets (R04). |
| `/api/v1/queries/validate` | `POST` | Phase 2 | Performs AST syntax check; blocks microdata queries (R07). |
| `/api/v1/queries/execute` | `POST` | Phase 3 | Submits query to DP noise mechanism with budget check (R08, R09). |
| `/api/v1/privacy/budget` | `GET` | Phase 3 | Returns remaining cumulative epsilon ledger balance (R09). |
| `/api/v1/privacy/receipts/{id}` | `GET` | Phase 5 | Retrieves signed, verifiable Privacy Receipt (R15). |
| `/api/v1/audit/verify` | `POST` | Phase 5 | Cryptographically verifies log chain integrity (R16). |
| `/api/v1/evaluations/report` | `GET` | Phase 4 | Returns empirical risk & utility benchmark report (R10, R13, R18). |

