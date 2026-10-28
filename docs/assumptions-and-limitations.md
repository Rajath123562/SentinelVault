# HOTFIX — Assumptions, Dependencies, and Known Limitations

**Project Name**: HOTFIX Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Current Phase**: Phase 1 Foundation  
**Version**: 1.0.0

---

## 1. Unresolved External Dependencies & Unknowns

In strict compliance with **Rule 3 (Do not invent official resources)**, items that are not present in the workspace are formally catalogued as **UNKNOWN** or **UNAVAILABLE**. No values have been invented:

| Architectural Parameter | Current Operational Value | Official Source Status | Impact on Architecture |
| :--- | :--- | :--- | :--- |
| **Official Datasets** | `UNAVAILABLE` | Not found in workspace. | Real data ingestion and schema binding deferred to Phase 2. |
| **Official Accounting Specification** | `NOT_CONFIGURED` | Not found in workspace. | Differential privacy accountant implementation deferred to Phase 3. Fail-closed release block enforced. |
| **Official Risk / Evaluation Harness** | `NOT_INTEGRATED` | Not found in workspace. | Attack simulations (MIA/re-identification) deferred to Phase 4. |
| **Dataset Privacy Unit** | `UNKNOWN` (None assigned) | Awaiting official dataset documentation. | Determining whether privacy applies per patient, per visit, per customer, or per transaction is deferred until official specification is confirmed. |
| **Adjacency Definition** | `UNKNOWN` (Add/Remove vs Substitute) | Awaiting official specification. | Determines whether bounded or unbounded DP mechanisms apply. |
| **Contribution Bounding Rules** | `UNKNOWN` (Max records per user unconfirmed) | Awaiting official specification. | User contribution truncation logic cannot be set prematurely. |
| **Privacy Accounting Method** | `UNKNOWN` (Rényi DP, PLD, or Basic Composition) | Awaiting official specification. | Target mission cumulative cap $\epsilon \le 5.0$ is preserved, but exact composition accounting method is deferred to Phase 3. |
| **Risk Metrics & Thresholds** | `UNKNOWN` | Awaiting official harness. | Quantitative thresholds for blocking high-threat queries cannot be arbitrarily invented. |
| **Prediction Task Requirements** | `UNKNOWN` | Awaiting challenge clarification. | ML model architecture and training targets deferred to Phase 4. |

---

## 2. Documented Engineering Assumptions

The following engineering decisions have been made to establish a production-grade Phase 1 foundation:

1. **Local Development Environment**:
   * Assumed local development on Windows 11 targeting Python 3.11+ and Node.js 20+.
   * Used standard lightweight dependencies (`fastapi`, `pydantic`, `pyyaml`, `httpx`, `pytest`, `react`, `vite`, `vitest`).
   * No heavy GPU frameworks, LLM libraries, or federated learning frameworks were introduced in Phase 1.
2. **Fail-Closed Release Policy**:
   * It is assumed that zero data release is permitted under any circumstances until the differential privacy engine and official accounting specification are verified.
   * Attempting to enable releases in configuration while the specification is unconfigured triggers a fatal validation failure.
3. **Database Architecture**:
   * SQLite is assumed as the primary lightweight relational store for local development; PostgreSQL connection strings are supported in schema definitions for production deployment.
   * Persistent database transactions are deferred to Phase 2.

---

## 3. Known Limitations of Phase 1 Build

1. **No Data Release**:
   * The Phase 1 gateway cannot answer analytical queries with differential privacy noise because the DP engine is scheduled for Phase 3.
2. **No User Authentication**:
   * Login screens and token verification are scheduled for Phase 2. The Phase 1 frontend reflects system status only.
3. **Synthetic Data Absence**:
   * No queries can be executed against official challenge datasets until they are placed in the workspace and validated in Phase 2.
