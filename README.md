# HOTFIX — Privacy-by-Design Analytics Gateway

[![Project Phase](https://img.shields.io/badge/Phase-Phase%201%20Foundation-blue.svg)](#)
[![Privacy Releases](https://img.shields.io/badge/Privacy%20Releases-Disabled%20(Fail%20Closed)-red.svg)](#)
[![Tests Passing](https://img.shields.io/badge/Tests-22%2F22%20Passing-brightgreen.svg)](#)
[![Team](https://img.shields.io/badge/Team%20ID-UG%2059-indigo.svg)](#)
[![Track](https://img.shields.io/badge/Track-Privacy%20by%20Design-purple.svg)](#)

HOTFIX is a production-grade **Privacy-by-Design Analytics Gateway** designed for sensitive health records and financial transaction data. It allows authorized analysts to extract statistical insights without ever exposing individual microdata rows or risking membership inference attacks.

---

## 1. Project Identity & Mission

* **Project Name**: HOTFIX
* **Full Name**: HOTFIX Privacy-by-Design Analytics Gateway
* **Team ID**: UG 59
* **Track**: Privacy by Design — Unlock Data Without Exposing It
* **Domain**: Cybersecurity, Privacy Engineering, Responsible AI, Data Analytics & Machine Learning

### Core Architectural Workflow (Target Product):
$$\text{User Authentication} \to \text{Authorization (RBAC)} \to \text{Query Validation} \to \text{Sensitivity/Contribution Bounds} \to \text{Privacy Budget Check} \to \text{Differential Privacy Noise} \to \text{Risk Assessment} \to \text{Budget Commit} \to \text{Privacy Receipt} \to \text{Protected Result}$$

---

## 2. Phase 1 Implementation Status

Phase 1 establishes the verified software foundation, configuration subsystem, automated test harnesses, and client-server communication channels:

| Capability | Module / Layer | Phase 1 Status |
| :--- | :--- | :--- |
| **Application Process & Liveness** | FastAPI (`backend/app/main.py`) | **VERIFIED** (`GET /health`) |
| **Readiness & Lifecycle Probe** | FastAPI (`backend/app/api/routes/system.py`) | **VERIFIED** (`GET /ready`) |
| **Diagnostic Status API** | FastAPI (`backend/app/api/routes/system.py`) | **VERIFIED** (`GET /api/system/status`) |
| **Fail-Closed Privacy Release Gate** | Configuration Core (`backend/app/core/config.py`) | **VERIFIED** (Releases strictly blocked) |
| **Standardized Error Sanitization** | Pydantic Schema (`backend/app/schemas/system.py`) | **VERIFIED** (Zero stack trace leaks) |
| **Web Dashboard & Diagnostics** | React 19 + TypeScript + Vite (`frontend/src/`) | **VERIFIED** (Live API connection) |
| **Automated Testing Suite** | Pytest + Vitest (`backend/tests/`, `frontend/tests/`) | **VERIFIED** (22/22 tests passing) |
| **Requirements Traceability** | RTM (`docs/requirements-traceability.md`) | **VERIFIED** (R01–R21 mapped) |

> [!IMPORTANT]
> **Privacy Release Readiness**: In Phase 1, the differential privacy engine and official accounting specification have not yet been integrated. In accordance with the system's fail-closed security policy, all privacy releases remain **strictly disabled**.

---

## 3. Repository Architecture

```
HOTFIX/
├── config/
│   ├── app.yaml               # Validated application settings (host, port, CORS, logging)
│   └── spec.yaml              # Track 4 accounting spec placeholder (status: NOT_CONFIGURED)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application factory, middleware, exception handlers
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py      # Pydantic v2 settings validation & fail-closed release invariants
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── system.py  # /health, /ready, /api/system/status routes
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── system.py      # Pydantic models for status, health, and error contracts
│   ├── tests/
│   │   ├── test_health.py     # Tests B01, B02
│   │   ├── test_readiness.py  # Test B03
│   │   ├── test_system_status.py # Tests B04, B10, B11
│   │   ├── test_config.py     # Tests B05, B06, B07, B08
│   │   ├── test_error_safety.py  # Test B09
│   │   ├── test_regression.py # Test B12
│   │   └── fixtures/
│   │       └── sample_dataset_stub.json # Isolated non-official unit test fixture
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── StatusBanner.tsx
│   │   │   ├── CapabilityMatrix.tsx
│   │   │   └── ConnectionAlert.tsx
│   │   ├── services/
│   │   │   └── api.ts         # Centralized API service with timeout & schema validation
│   │   ├── types/
│   │   │   └── system.ts      # TypeScript interfaces
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── tests/
│   │   └── App.test.tsx       # Vitest + React Testing Library component tests
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── docs/
│   ├── phase1/
│   │   └── workspace-audit.md
│   ├── architecture.md
│   ├── requirements-traceability.md
│   ├── data-inventory.md
│   ├── api-contracts.md
│   ├── testing-strategy.md
│   ├── assumptions-and-limitations.md
│   └── SPEC_CONFORMANCE.md
├── scripts/
│   ├── run_backend.ps1        # Script to launch FastAPI server
│   ├── run_frontend.ps1       # Script to launch Vite dev server
│   └── test_all.ps1           # Comprehensive automated test runner
├── .gitignore
├── .env.example
├── README.md
└── PHASE_STATUS.md
```

---

## 4. Setup & Running Instructions

### Prerequisites
* **Python**: 3.11 or newer
* **Node.js**: v20 or newer (`npm` 10+)
* **PowerShell** (Windows) or **Bash** (macOS/Linux)

---

### Step 1: Environment Configuration
Copy `.env.example` to create your local `.env`:
```powershell
Copy-Item .env.example .env
```

---

### Step 2: Start the Backend Gateway

**Using the convenience script:**
```powershell
.\scripts\run_backend.ps1
```

**Or directly from the terminal:**
```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend starts at `http://127.0.0.1:8000`. You can verify:
* **Liveness**: `http://127.0.0.1:8000/health`
* **Readiness**: `http://127.0.0.1:8000/ready`
* **System Status**: `http://127.0.0.1:8000/api/system/status`
* **OpenAPI Docs**: `http://127.0.0.1:8000/docs`

---

### Step 3: Start the Frontend Interface

**Using the convenience script:**
```powershell
.\scripts\run_frontend.ps1
```

**Or directly from the terminal:**
```powershell
cd frontend
npm run dev
```

Open your browser to `http://localhost:5173`. The dashboard immediately connects to the backend and displays the verified system status.

---

## 5. Automated Test Execution

Execute the unified test suite across backend and frontend:

```powershell
.\scripts\test_all.ps1
```

### Individual Test Commands:

* **Backend Unit & API Tests (16 tests)**:
  ```powershell
  cd backend
  python -m pytest tests -v
  ```

* **Frontend Unit & Component Tests (6 tests)**:
  ```powershell
  cd frontend
  npm test
  ```

* **Frontend TypeScript Validation**:
  ```powershell
  cd frontend
  npm run typecheck
  ```

* **Frontend Production Build**:
  ```powershell
  cd frontend
  npm run build
  ```

---

## 6. Phase 1 Acceptance Gate Conformance

All 15 mandatory Phase 1 acceptance gates have been satisfied and empirically verified:

* [x] **GATE 01**: Workspace audit completed (`docs/phase1/workspace-audit.md`).
* [x] **GATE 02**: Requirements traceability matrix created (R01–R21 mapped).
* [x] **GATE 03**: System architecture and trust boundaries documented (`docs/architecture.md`).
* [x] **GATE 04**: Backend initializes and `GET /health` passes.
* [x] **GATE 05**: Frontend connects and displays live status from backend.
* [x] **GATE 06**: Application configuration is validated by Pydantic.
* [x] **GATE 07**: Privacy releases remain disabled (fail-closed enforced).
* [x] **GATE 08**: Missing or invalid official spec cannot silently enable releases.
* [x] **GATE 09**: Backend unit and API tests pass (16/16).
* [x] **GATE 10**: Frontend tests (6/6) and production build pass.
* [x] **GATE 11**: Static TypeScript and lint checks pass (0 errors).
* [x] **GATE 12**: Regression release guard route `/api/v1/query/release` verified (HTTP 403).
* [x] **GATE 13**: Startup and run commands verified empirically in local terminal.
* [x] **GATE 14**: No mock or simulated code presented as production functionality.
* [x] **GATE 15**: Test execution report records exact commands, exit codes, and evidence.

---

## 7. Next Steps: Phase 2 Handoff

Phase 2 will implement:
1. User Authentication and 5-attempt lockout (R01, R02).
2. Role-Based Access Control for Analysts and Administrators (R03).
3. Ingestion and verification of official synthetic health and financial datasets (R04).
4. PII and quasi-identifier classification (R05).
5. Restricted analytical query parser blocking microdata extraction (R07).

See `PHASE_STATUS.md` for full handoff details.
