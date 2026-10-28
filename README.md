# HOTFIX — Privacy-by-Design Analytics Gateway

[![Project Phase](https://img.shields.io/badge/Milestone-MVP%20Verified-brightgreen.svg)](#)
[![Differential Privacy](https://img.shields.io/badge/Mechanism-Laplace%20(diffprivlib)-blue.svg)](#)
[![Budget Ledger](https://img.shields.io/badge/Budget%20Cap-ε%20%E2%89%A4%205.0-orange.svg)](#)
[![Cryptography](https://img.shields.io/badge/Signatures-Ed25519%20%2B%20SHA--256-indigo.svg)](#)
[![Tests Passing](https://img.shields.io/badge/Tests-54%2F54%20Passing-brightgreen.svg)](#)
[![Team](https://img.shields.io/badge/Team%20ID-UG%2059-purple.svg)](#)
[![Track](https://img.shields.io/badge/Track-Privacy%20by%20Design-purple.svg)](#)

HOTFIX is an enterprise-grade **Privacy-by-Design Analytics Gateway** engineered for sensitive health records and financial transactions. It enables authorized analysts to query aggregate statistical insights without exposing underlying individual records, risking re-identification, or exceeding strict privacy budget caps.

---

## 1. Project Identity & Mission

* **Project Name**: HOTFIX
* **Full Name**: HOTFIX Privacy-by-Design Analytics Gateway
* **Team ID**: UG 59
* **Track**: Privacy by Design — Unlock Data Without Exposing It
* **Domain**: Cybersecurity, Privacy Engineering, Responsible AI, Data Analytics & Machine Learning

### Core Architectural Pipeline:
```
LOGIN (PBKDF2-HMAC-SHA256, 5-Attempt Lockout)
  ↓
AUTHORIZATION & SCOPING (Analyst / Data Steward / Auditor)
  ↓
DATASET SELECTION (Synthetic Health / Financial Records, 500 rows each)
  ↓
QUERY VALIDATION (COUNT DISTINCT Privacy Unit, Allowlist Grammar, Sensitivity Δf = 1.0)
  ↓
PRE-RELEASE PRIVACY POLICY CHECK (Sensitive Field Redaction, Parameter Bounds)
  ↓
BUDGET RESERVATION (SQLite Atomic Transaction BEGIN IMMEDIATE, Cap ε ≤ 5.0, Micro-epsilon integer math)
  ↓
DIFFERENTIAL PRIVACY MECHANISM (IBM diffprivlib Laplace with bounded CSPRNG fallback)
  ↓
COMMITTED ACCOUNTING & CRYPTOGRAPHIC AUDIT RECORD (SHA-256 Hash Chain + Ed25519 Gateway Keypair Signature)
  ↓
VERIFIABLE PRIVACY RECEIPT (Self-contained JSON receipt returned to client)
```

---

## 2. Key MVP Capabilities

1. **Zero-Trust Authentication & Lockout**: PBKDF2-HMAC-SHA256 password hashing with 100,000 iterations. Automatically triggers a 15-minute temporary lockout after 5 consecutive failed login attempts (HTTP 429).
2. **Restricted Query Engine**: Allowlist grammar strictly permitting `COUNT DISTINCT` over approved categorical fields (`diagnosis_category`, `admission_type`, `age_group` for health; `transaction_type`, `risk_band`, `account_type` for financial). Arbitrary SQL, individual row filtering, and direct identifier queries (SSN, MRN) are rejected with HTTP 400.
3. **Distinct Privacy Unit Sensitivity**: Queries compute distinct privacy units (`patient_id` or `customer_id`), mathematically guaranteeing global sensitivity $\Delta f = 1.0$ even if an individual has multiple transaction or clinical encounter rows.
4. **Differential Privacy Noise Mechanism**: Real Laplace mechanism via IBM `diffprivlib` with bounded CSPRNG fallback. Releases noisy non-negative integers ($\ge 0$). Raw counts are never returned to the analyst.
5. **Shared Privacy Budget Ledger**: Shared SQLite budget ledger enforcing a strict dataset cap ($\epsilon \le 5.0$). Uses exact integer micro-epsilon math ($1.0 = 1,000,000 \mu\epsilon$) to prevent floating-point drift. Enforces concurrency safety via atomic `BEGIN IMMEDIATE` transactions.
6. **Repeated-Query Caching**: Submitting an identical query with the same $\epsilon$ reuses the previous release at **0 budget cost**, preventing budget drain and noise-averaging attacks.
7. **Verifiable Privacy Receipts**: Every release produces a tamper-evident receipt containing query description, fingerprint, mechanism, $\epsilon$ spent, cumulative $\epsilon$, remaining budget, policy status, SHA-256 audit entry hash, and an **Ed25519 digital signature**.
8. **Cryptographic Audit Ledger**: Append-only SHA-256 hash-chained log digitally signed by the gateway authority keypair. Any tampering or hash pointer breakage is detected immediately.
9. **Empirical Utility Benchmark**: Automated empirical test suite running 50 trials per $\epsilon \in \{0.1, 0.2, 0.5, 1.0\}$, verifying the theoretical inverse relationship between $\epsilon$ and noise error (MAE & RMSE).
10. **Modern React Frontend**: Clean, responsive, dark-mode cybersecurity dashboard with 4 comprehensive views:
    * **View A**: Authentication & Rate-Limit Lockout Feedback.
    * **View B**: Analytics Query Builder, Sensitivity Pre-flight, and Real-time Budget Progress Bar.
    * **View C**: Cryptographic Privacy Receipt Inspector with JSON copy/download.
    * **View D**: Audit Ledger Cryptographic Verification & Empirical Utility Benchmark Report.

---

## 3. Quick Start Guide (Windows PowerShell)

### Prerequisites
* Python 3.11+
* Node.js 18+ and npm

### 1. Run Complete Automated Test Suite (Recommended First Step)
To verify all 44 backend tests, the empirical utility benchmark, TypeScript validation, and 10 frontend tests:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1
```

### 2. Start Backend API Gateway
Open a PowerShell terminal and run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_backend.ps1
```
*Backend will start on `http://127.0.0.1:8000`.*
* Interactive API Documentation (Swagger): `http://127.0.0.1:8000/docs`
* Health Probe: `http://127.0.0.1:8000/health`
* Readiness Probe: `http://127.0.0.1:8000/ready`
* System Status: `http://127.0.0.1:8000/api/system/status`

### 3. Start Frontend Dashboard
Open a second PowerShell terminal and run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_frontend.ps1
```
*Frontend will launch on `http://localhost:5173`.*

---

## 4. Default Seeded Credentials

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `analyst_user` | `AnalystPass2026!` | `analyst` | Can submit approved analytical queries, inspect receipts, and view utility benchmarks. |
| `steward_user` | `StewardPass2026!` | `data_steward` | Can monitor dataset budgets, sensitivity bounds, and policy rules. |
| `auditor_user` | `AuditorPass2026!` | `auditor` | Can run cryptographic audit ledger verification and tamper-detection checks. |

*(All users have 5-attempt rate-limiting with a 15-minute temporary lockout).*

---

## 5. Live Demonstration Script (3-Minute Hackathon Demo)

1. **Step 1 — Authenticated Login & Rate Limiting**:
   * Navigate to `http://localhost:5173`.
   * Click quick-fill button **Analyst** (`analyst_user` / `AnalystPass2026!`).
   * Click **Sign In to Gateway**.
   *(To demonstrate lockout: enter 5 incorrect passwords to see the 15-minute temporary lockout banner).*
2. **Step 2 — Analytical Query & Differential Privacy Release**:
   * On the **Analytics Dashboard**, select the **Health** dataset (500 records, privacy unit: `patient_id`).
   * Note the **Shared Privacy Budget Bar** showing 5.00 $\epsilon$ remaining.
   * Under Query Specification, select `diagnosis_category = cardiovascular` and $\epsilon = 0.5$.
   * Click **Validate & Preview**: Observe pre-flight gate passing with bounded sensitivity $\Delta f = 1.0$.
   * Click **Execute Differential Privacy Release**:
     * Observe the committed noisy count (e.g., 104 vs exact concealed 100).
     * Observe budget deduction: Spent: 0.50 $\epsilon$, Remaining: 4.50 $\epsilon$.
3. **Step 3 — Zero-Cost Query Caching**:
   * Click **Execute Differential Privacy Release** again with the exact same parameters.
   * Observe the **⚡ CACHE HIT (0.00 ε SPENT)** badge! No budget is deducted, preventing noise-averaging attacks.
4. **Step 4 — Verifiable Privacy Receipt**:
   * Click **📜 View Cryptographic Privacy Receipt**.
   * Observe the self-contained receipt displaying query description, $\epsilon$ expenditure, SHA-256 audit entry hash pointer, and authentic **Ed25519 digital signature**.
5. **Step 5 — Cryptographic Audit Verification & Empirical Utility**:
   * Click the **🛡️ Cryptographic Audit & Utility** tab in the header.
   * Click **🔄 Re-verify Audit Ledger**: Observe **AUDIT CHAIN INTEGRITY VERIFIED** across all entries using SHA-256 hash chaining and Ed25519 signature checks.
   * Scroll to the **Empirical Privacy-Utility Trade-off Benchmark** table to demonstrate empirical proof of Laplace noise scaling across 50 trials per $\epsilon$.

---

## 6. Official Track 4 Transparency Disclosure

In strict adherence to our anti-fakery and honest engineering contract:
* **Official Accounting Specification**: `DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED` (Demonstration accounting uses integer micro-epsilon arithmetic on SQLite; pending official Track 4 specification).
* **Official Empirical Risk Evaluation**: `OFFICIAL EMPIRICAL RISK EVALUATION NOT CONFIGURED` (No synthetic attack scores are fabricated; pending official Track 4 evaluation harness).
