# SentinelVault — Phase 7 Baseline Architecture & System Integration Report

**Product:** SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Tagline:** *Analyze Data. Don't Expose It.*  
**Team:** HOTFIX (Team ID: UG 59)  
**Track:** Track 4: Privacy by Design  
**Date:** October 29, 2026  
**Document ID:** `13-phase7-baseline-inspection-report.md`  

---

## 1. Executive Baseline Summary

Phase 7 marks the culmination of the SentinelVault system development lifecycle: unifying all 16 frontend screens, the FastAPI backend, differential privacy noise mechanisms, transactional micro-epsilon ledgers, cryptographic SHA-256 audit hash chains, Ed25519 privacy receipts, SIEM security events, and the fail-closed incident response state machine into a cohesive, production-grade application.

Prior to Phase 7, several key features operated successfully in isolation or were demonstrated via API tests, but exhibited minor end-to-end integration frictions and presentation discrepancies. This report documents the baseline audit, catalog of existing components, identified contract mismatches, and the architectural resolutions applied.

---

## 2. Inventory of Implemented Components

### 2.1 16-Screen Frontend Architecture (React 19 / TypeScript / Vite / Tailwind)
1. **Screen 1: Login Page** (`AuthView.tsx`) — Zero-trust authentication with PBKDF2 salt-derived session keys and 5-attempt brute-force lockout indicator.
2. **Screen 2: Dashboard Home** (`DashboardHomeView.tsx`) — 4 live KPI metric cards (Active Datasets, Remaining Budget, Cryptographic Receipts, Verified Audit Entries) and Recent Activity ledger.
3. **Screen 3: Dataset Selection** (`DatasetSelectionView.tsx`) — Searchable catalog for Synthetic Health Records and Financial Transactions with privacy unit metadata and schema allowlists.
4. **Screen 4: Query Builder** (`QueryBuilderView.tsx`) — Guided parameter controls, epsilon slider (0.10–1.00), and live SQL sandbox syntax preview.
5. **Screen 5: Query Results** (`QueryResultsView.tsx`) — Differentially private count card with Laplace noise metrics, budget deduction breakdown, and receipt navigation link.
6. **Screen 6: Privacy Budget** (`PrivacyBudgetView.tsx`) — Circular SVG ring meter displaying consumed vs remaining allowance, and micro-epsilon usage ledger table.
7. **Screen 7: Privacy Receipts** (`PrivacyReceiptViewer.tsx`) — Verifiable cryptographic receipt visualizer displaying Ed25519 enclave digital signature, SHA-256 canonical hash, and JSON export.
8. **Screen 8: Audit Logs** (`AuditEvaluationView.tsx`) — Immutable hash chain viewer with live SHA-256 link verification and search filters.
9. **Screen 9: Security Events & SIEM Alerts** (`SecurityEventsView.tsx`) — Centralized event ledger with severity tags and steward triage actions.
10. **Screen 10: User Management** (`UserManagementView.tsx`) — Role-gated admin portal for user status inspection and lockout remediation.
11. **Screen 11: Mobile Responsive Navigation** (`Sidebar.tsx`, `App.tsx`) — Slide-out drawer and bottom quick-action bar for mobile devices.
12. **Screen 12: Loading & Error Modal** (`LoadingModal.tsx`, `ErrorBoundary.tsx`) — Graceful processing spinners and unhandled exception barriers.
13. **Screen 13: Access Denied** (`AccessDeniedView.tsx`) — Shielded error screen on RBAC authorization failures.
14. **Screen 14: Settings & Diagnostics** (`SettingsView.tsx`) — System health probe status, TOTP MFA enrollment, and session termination.
15. **Screen 15: About & Trust Pillars** (`AboutView.tsx`) — Mission briefing and Privacy-by-Design architectural guarantees.
16. **Screen 16: Not Found (404)** (`NotFoundView.tsx`) — Fallback route screen with safe navigation back to Dashboard.

### 2.2 Backend Microservices (FastAPI / SQLite / diffprivlib / cryptography)
* **Authentication Engine** (`auth_service.py`): PBKDF2-HMAC-SHA256 password hashing (600,000 rounds), per-user salts, 5-attempt lockout (15-min TTL), TOTP MFA enrollment.
* **Granular RBAC Engine** (`auth_service.py`): Hierarchical permissions across `analyst`, `data_steward`, `auditor`, and `admin` roles.
* **Vault Data Isolation** (`query_engine.py`): Strictly separated `health_records_demo.json` and `financial_transactions_demo.json` fixtures. Direct row access rejected.
* **Differential Privacy Engine** (`privacy_engine.py`): Pure $(\varepsilon, 0)$-DP Laplace mechanism with bounded CSPRNG, sensitivity $\Delta f = 1.0$, and allowlisted epsilons $[0.1, 0.25, 0.5, 0.75, 1.0]$.
* **Micro-Epsilon Ledger** (`query_engine.py`): SQLite `BEGIN IMMEDIATE` atomic serialization preventing double-spends and floating-point rounding errors.
* **Receipt & Audit Engine** (`crypto_audit.py`): RFC 8032 Ed25519 digital signatures, canonical JCS JSON hashing, and forward-secure SHA-256 hash chaining.
* **Incident Response State Machine** (`incident_service.py`): 3 operational states (`NORMAL`, `RESTRICTED`, `RELEASES_DISABLED`) enforcing fail-closed release gating.

---

## 3. Baseline Inconsistencies & Remediation Plan

### Inconsistency #1: Query Preview `COUNT(*)` vs Receipt `COUNT_DISTINCT(privacy_unit)`
* **Baseline Observation:** In previous releases, `QueryPreviewResponse` generated a generic `SELECT COUNT(*) FROM table WHERE field = 'value'` string, while the differential privacy engine calculated `COUNT_DISTINCT(patient_id)` and the privacy receipt recorded `COUNT_DISTINCT(patient_id)`.
* **Privacy Impact:** If an individual contributes multiple encounters, a raw `COUNT(*)` has global sensitivity $\Delta f > 1.0$, which would require larger noise or leak membership. To maintain $\Delta f = 1.0$, the gateway strictly counts distinct privacy units (`patient_id` or `account_id`).
* **Remediation:** 
  1. Updated `QueryPreviewResponse` schema in `mvp.py` and `types/system.ts` to include `logical_query`, `privacy_unit`, and `global_sensitivity`.
  2. Authoritatively computed `logical_query = f"SELECT COUNT_DISTINCT({privacy_unit}) AS noisy_count FROM {dataset_id}_vault WHERE {field} = '{value}'"`.
  3. Bound frontend `QueryBuilderView.tsx` to render the exact `preview.logical_query` string, ensuring syntax, computation, receipt, and audit entry describe identical semantics.

### Inconsistency #2: Privacy Budget Ledger Reconciliation
* **Baseline Observation:** The visual circular SVG meter showed 0.50 ε used / 4.50 ε remaining, while the hardcoded fallback list in the frontend contained static demo items (0.80, 0.40, 0.14 ε).
* **Remediation:** 
  1. Extended `BudgetStatusResponse` schema to include `recent_releases: List[BudgetRecentRelease]`.
  2. Implemented query in `query_engine.py`: `SELECT release_id, query_description, epsilon_spent, cumulative_epsilon, timestamp FROM privacy_receipts WHERE dataset_id = ? ORDER BY timestamp DESC LIMIT 10`.
  3. Updated `PrivacyBudgetView.tsx` to render authoritative `localBudget.recent_releases` with empty state when zero releases exist.

### Inconsistency #3: Operator Flexibility (`=` vs `equals`)
* **Baseline Observation:** Frontend dropdowns and manual queries passing the mathematical symbol `=` were rejected with `Unsupported operator '='. MVP strictly supports 'equals'`.
* **Remediation:** Implemented case-insensitive normalization in `query_engine.py`: `norm_op = "equals" if str(operator).strip().lower() in {"equals", "="} else str(operator).strip().lower()`. Both notations now map to identical canonical execution.

### Inconsistency #4: Zero-Trust Session Restoration on Refresh
* **Baseline Observation:** Browser page reloads dropped authenticated state, requiring repeated sign-in.
* **Remediation:** Implemented `getMe(token)` calling `GET /api/me`. In `App.tsx`, mount-time hook validates stored `sessionStorage` token before restoring session. If expired or revoked, session drops safely to login.

---

## 4. Master Integration Testing Strategy

The Phase 7 verification layer establishes a dedicated end-to-end integration test file (`backend/tests/test_phase7_fullstack_integration.py`) covering 30+ comprehensive scenarios:
* Full query lifecycle across both datasets (`health` and `financial`).
* Complete authorization matrix across all 4 roles.
* Tamper detection tripwires and incident state transitions.
* Concurrency races and atomic budget guarantees.
* Parity between preview, execution, and receipt records.

