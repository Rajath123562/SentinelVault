# SentinelVault — Master Defect Register & Remediation Log

**Document Identifier**: SV-DEF-2026-V1  
**Project**: SentinelVault (Zero-Trust Privacy-Preserving Analytics Gateway)  
**Team**: HOTFIX (UG 59)  
**Date**: October 29, 2026  
**Status**: All Discovered Defects Fully Remediated (Zero Open Critical/High Defects)

---

## 1. Defect Classification Summary

| Severity | Discovered | Remediated | Open | Verification Status |
| :--- | :---: | :---: | :---: | :---: |
| **Critical** | 3 | 3 | 0 | **VERIFIED** |
| **High** | 3 | 3 | 0 | **VERIFIED** |
| **Medium** | 2 | 2 | 0 | **VERIFIED** |
| **Low** | 0 | 0 | 0 | **VERIFIED** |
| **TOTAL** | **8** | **8** | **0** | **100% REMEDIATED** |

---

## 2. Granular Defect Logs

### DEF-01: Skill Frontmatter Multiline Formatting Failure
- **Severity**: High (Tooling / Agent Orchestration)
- **Component**: Global Skill Configuration (`universal-project-orchestrator/SKILL.md`)
- **Symptom**: System-level parsing exception on skill YAML frontmatter preventing skill activation.
- **Root Cause**: Multiline unquoted description string failed strict PyYAML parsing.
- **Remediation**: Re-formatted frontmatter description into a clean, double-quoted single-line string.
- **Verification**: Skill loader verified clean parsing; zero startup warnings.

---

### DEF-02: Frontend Blank Screen on Initial Launch
- **Severity**: Critical (User Interface / User Experience)
- **Component**: Frontend (`frontend/src/index.css`, `frontend/vite.config.ts`)
- **Symptom**: Navigating to `http://localhost:5173/` rendered a completely blank dark page; browser console showed CSS compilation failures.
- **Root Cause**: Vite 6 / Tailwind CSS v4 required `@tailwindcss/vite` plugin and `@import "tailwindcss";` instead of legacy `@tailwind` directives.
- **Remediation**: Installed `@tailwindcss/vite`, added plugin to `vite.config.ts`, updated `frontend/src/index.css`, and restarted Vite dev server.
- **Verification**: Verified via `npm run build` (0 errors) and live browser rendering.

---

### DEF-03: Query Engine Rejection of Standard Equals Operator (`=`)
- **Severity**: Critical (Core Query Pipeline)
- **Component**: Backend Query Engine (`backend/app/services/query_engine.py`, `frontend/src/App.tsx`)
- **Symptom**: Query Builder execution rejected with: `Query Error: Unsupported operator '='. MVP strictly supports 'equals'`.
- **Root Cause**: Frontend query preview was emitting `'='` while query validation strictly expected `'equals'`.
- **Remediation**: Updated `validate_query` and `compute_query_fingerprint` in `query_engine.py` to accept and normalize both `'='` and `'equals'`. Aligned `App.tsx` query runner.
- **Verification**: Verified via HTTP POST `/api/queries/run` returning 200 OK with Laplace noise and signed receipt.

---

### DEF-04: Missing TOTP Helper Function in Authentication Service
- **Severity**: Medium (Authentication & MFA)
- **Component**: Backend Auth Service (`backend/app/services/auth_service.py`)
- **Symptom**: `ImportError: cannot import name 'generate_totp_code' from 'app.services.auth_service'`.
- **Root Cause**: `compute_totp_code` was implemented but convenience wrapper `generate_totp_code` was missing.
- **Remediation**: Added `generate_totp_code(secret_b32)` delegating to `compute_totp_code(secret_b32, time.time() // 30)`.
- **Verification**: Verified in `test_auth_deep.py` (all 42 scenarios passed).

---

### DEF-05: SQLite NOT NULL Constraint Failure in Test Seed
- **Severity**: Medium (Database Testing Infrastructure)
- **Component**: Database Seed (`backend/tests/test_auth_deep.py`)
- **Symptom**: `sqlite3.IntegrityError: NOT NULL constraint failed: users.created_at`.
- **Root Cause**: Test fixture inserted a new user without supplying mandatory `created_at` timestamp column.
- **Remediation**: Supplied `datetime.now(timezone.utc).isoformat()` in fixture query.
- **Verification**: Fixture executes cleanly; 0 integrity errors.

---

### DEF-06: Client-Side URL Null Byte Handling Exception
- **Severity**: Medium (API Contract Testing)
- **Component**: Test Suite (`backend/tests/test_vault_query_deep.py`)
- **Symptom**: `httpx.InvalidURL: Invalid non-printable ASCII character in URL, '\x00'`.
- **Root Cause**: Python `httpx` client rejects raw null bytes client-side before sending HTTP request to server.
- **Remediation**: Replaced raw `\x00` with URL-encoded representation `%00` to properly test server-side path traversal defense.
- **Verification**: Server properly rejects encoded traversal with HTTP 400/404; test passed.

---

### DEF-07: Financial Fixture Schema Field Mismatch
- **Severity**: High (Data Vault Schema Conformance)
- **Component**: Test Suite (`backend/tests/test_vault_query_deep.py`)
- **Symptom**: Queries on financial dataset rejected with `Field 'risk_category' is not in approved allowlist`.
- **Root Cause**: Fixture `financial_transactions_demo.json` defines field as `risk_band` (values: `low`, `medium`, `high`) and transaction type `wire` (not `wire_transfer`).
- **Remediation**: Aligned test assertions and query payloads to official approved schema in `financial_transactions_demo.json`.
- **Verification**: Verified in `test_vault_query_deep.py` (36 / 36 passed).

---

### DEF-08: Incomplete SIEM Security Event Telemetry Recording
- **Severity**: Critical (Zero-Trust Security & Auditing)
- **Component**: Query Engine & Auth Service (`query_engine.py`, `auth_service.py`)
- **Symptom**: Failed logins, policy violations, and budget exhaustion attempts were not persistently logged to `security_events` table.
- **Root Cause**: `record_security_event_db` was not called during query validation/budget exhaustion, and was uncommitted in auth service.
- **Remediation**: Instrumented `execute_query_pipeline` and `login_user` to record structured security events with `action`, `resource`, `actor`, and `outcome`, wrapped in SQLite transaction commits.
- **Verification**: Verified in `test_receipts_audit_deep.py` (25 / 25 passed).

