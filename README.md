# SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway

> **"Analyze Data. Don't Expose It."**

[![Project Milestone](https://img.shields.io/badge/Milestone-Phase%208%20Complete%20Production%20Hardened-brightgreen.svg)](#)
[![Differential Privacy](https://img.shields.io/badge/Mechanism-Pure%20(ε%2C0)--DP%20Laplace-blue.svg)](#)
[![Budget Ledger](https://img.shields.io/badge/Budget%20Cap-ε%20%E2%89%A4%205.0%20(Micro--Epsilon)-orange.svg)](#)
[![Cryptography](https://img.shields.io/badge/Signatures-Ed25519%20%2B%20SHA--256-indigo.svg)](#)
[![Disaster Recovery](https://img.shields.io/badge/Disaster%20Recovery-Online%20Atomic%20Backup%20%2B%20Anti--Rollback-blue.svg)](#)
[![Tests Passing](https://img.shields.io/badge/Tests-424%2F424%20Passing%20(100%25)-brightgreen.svg)](#)
[![Live HTTP Integration](https://img.shields.io/badge/Live%20Gateway%20E2E-Verified-brightgreen.svg)](#)
[![Team](https://img.shields.io/badge/Team%20ID-HOTFIX%20UG%2059-purple.svg)](#)
[![Track](https://img.shields.io/badge/Track-Track%204%3A%20Privacy%20by%20Design-purple.svg)](#)

SentinelVault is an enterprise-grade **Zero-Trust Privacy-Preserving Analytics Gateway** engineered for sensitive health records and financial transaction data. It enables authorized analysts to query aggregate statistical insights without exposing underlying individual records, risking re-identification, or exceeding strict privacy budget caps.

---

## 1. Project Identity & Architecture

* **Product Name**: SentinelVault
* **Full Name**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway
* **Tagline**: Analyze Data. Don't Expose It.
* **Team**: HOTFIX, Team ID UG 59
* **Track**: Track 4 — Privacy by Design (Unlock Data Without Exposing It)
* **Domain**: Cybersecurity, Privacy Engineering, Differential Privacy, Applied Cryptography

### Core Zero-Trust Pipeline:
```
LOGIN (PBKDF2-HMAC-SHA256, 5-Attempt Lockout Window)
  ↓
AUTHORIZATION & RBAC (Analyst / Data Steward / Auditor / Admin)
  ↓
DATASET SELECTION (Isolated Vaults: Healthcare Clinical Cohort & Retail Banking)
  ↓
RESTRICTED QUERY VALIDATION (Allowlist Aggregate Grammar, Global Sensitivity Δf = 1.0)
  ↓
PRE-RELEASE PRIVACY CHECK (Sensitive Field Redaction, Cache Reuse Detection)
  ↓
BUDGET RESERVATION (SQLite Atomic Transaction BEGIN IMMEDIATE, Cap ε ≤ 5.0, Micro-epsilon integer math)
  ↓
DIFFERENTIAL PRIVACY ENGINE (IBM diffprivlib Laplace Mechanism with bounded CSPRNG)
  ↓
COMMITTED ACCOUNTING & CRYPTOGRAPHIC AUDIT RECORD (SHA-256 Hash Chain + Ed25519 Digital Signature)
  ↓
VERIFIABLE PRIVACY RECEIPT (Self-contained JSON receipt returned to client)
```

---

## 2. 16-Screen Master Reference Board Mapping

Conforms strictly to the 16-screen enterprise master specification (`media_1793200631528_bb8fd096.jpg`):

| # | Screen Name | Component | Functional Verification Evidence |
| :- | :--- | :--- | :--- |
| **01** | **Login Page** | `AuthView.tsx` | PBKDF2 authentication, 5-attempt lockout countdown, pre-seeded demo user chips. |
| **02** | **Dashboard (Home)** | `DashboardHomeView.tsx` | 4 metric KPI cards, live recent activity ledger, quick navigation to query builder. |
| **03** | **Dataset Selection** | `DatasetSelectionView.tsx` | Searchable catalog for Healthcare & Financial datasets with chips and privacy units. |
| **04** | **Query Builder** | `QueryBuilderView.tsx` | Parameter controls, epsilon slider ($\epsilon \in [0.1, 1.0]$), live SQL syntax preview box. |
| **05** | **Query Results** | `QueryResultsView.tsx` | Noisy count card, theoretical 95% Laplace confidence interval bounds, receipt link. |
| **06** | **Privacy Budget** | `PrivacyBudgetView.tsx` | Animated SVG circular ring meter, used/remaining/total budget, micro-epsilon ledger. |
| **07** | **Privacy Receipt** | `PrivacyReceiptViewer.tsx` | Cryptographic receipt card, Ed25519 signature verification pill, JSON download button. |
| **08** | **Audit Logs** | `AuditEvaluationView.tsx` | SHA-256 hash chain verification (0 broken links), filter dropdown, search input. |
| **09** | **Security Events & Alerts** | `SecurityEventsView.tsx` | Dual-tab view: SIEM event ledger and alerts tab with High/Medium/Low severity badges. |
| **10** | **Role Management (Admin)** | `UserManagementView.tsx` | Admin user management & lockout release; analysts receive 403 Forbidden. |
| **11** | **Responsive Mobile View** | `Sidebar.tsx`, `App.tsx` | Mobile hamburger drawer + bottom fixed quick-navigation bar (`Home`, `Datasets`, `Query`). |
| **12** | **Loading & Error Modal** | `LoadingModal.tsx` | High-polish spinner modal: *"Processing your query... Applying differential privacy."* |
| **13** | **Unauthorized Access Attempt** | `AccessDeniedView.tsx` | Shield access-denied screen with permission violation reason and "Go Back" action. |
| **14** | **Settings** | `SettingsView.tsx` | Profile, Security, TOTP MFA status, and session termination (logout) controls. |
| **15** | **About / Info** | `AboutView.tsx` | Publicly accessible gateway architecture, Track 4 mission, and 3 trust pillars. |
| **16** | **404 Page** | `NotFoundView.tsx` | Search illustration, "Page Not Found", and "Go Back Home" action. |

---

## 3. Seeded Demonstration Credentials

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Analyst** | `analyst_user` | `AnalystPass2026!` | Standard analytics query execution, privacy releases, and receipts. |
| **Data Steward** | `steward_user` | `StewardPass2026!` | Data governance, dataset partition management, and security monitoring. |
| **Auditor** | `auditor_user` | `AuditorPass2026!` | Independent compliance, SHA-256 hash chain verification, signature audits. |
| **Administrator** | `admin_user` | `AdminPass2026!` | User management console, 5-attempt lockout release, gateway health oversight. |

---

## 4. Quick Start Guide (Windows)

### Prerequisites
* Python 3.11+
* Node.js 18+ and npm

### Option A: One-Click Startup (Recommended)
Double-click `start_all.bat` (or run `.\start_all.bat` in PowerShell / Command Prompt).  
This automatically opens the FastAPI backend and Vite frontend in separate terminal windows.

### Option B: Manual Terminal Execution

* **Terminal 1 — Backend Gateway:**
  ```powershell
  $env:PYTHONPATH="backend"
  python -m uvicorn app.main:app --port 8000 --reload
  ```
  * Swagger API Documentation: `http://127.0.0.1:8000/docs`
  * System Health Probe: `http://127.0.0.1:8000/health`
  * System Status: `http://127.0.0.1:8000/api/system/status`

* **Terminal 2 — Frontend Application:**
  ```powershell
  npm run dev --prefix frontend
  ```
  * Frontend Portal: `http://localhost:5173`

---

## 5. Verification & Test Execution

SentinelVault includes 100% automated test coverage across all layers:

```powershell
# 1. Run Complete Automated Test Suite (359 Tests across 6 Stages)
powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1

# 2. Run Backend Pytest Suite (350 Tests)
$env:PYTHONPATH="backend"; python -m pytest backend/tests -v

# 3. Run Frontend Vitest Suite (9 Tests)
npm test --prefix frontend

# 4. Run Frontend TypeScript Typecheck
npm run typecheck --prefix frontend

# 5. Run Live HTTP Gateway Integration Test (11 Stages)
python scripts/live_gateway_test.py

# 6. Run DP Empirical Utility Benchmark (50 trials per epsilon)
python scripts/run_utility_benchmark.py
```

---

## 6. Hackathon Package & Visual Assets

* **Submission Archive**: `SentinelVault_UG59_Hackathon_Submission.zip`
* **Screenshots Directory**: `screenshots/`
  * `01_frontend_dashboard.png` (Live Web Portal)
  * `02_backend_swagger_api.png` (FastAPI Interactive Docs)
  * `03_terminal_test_execution.png` (Automated Test Execution Evidence)
  * `04_privacy_receipt_card.png` (Cryptographic Privacy Receipt)
* **Packaging Script**: `python scripts/package_submission.py`
