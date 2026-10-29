# SentinelVault — Known Limitations & Architectural Boundaries

**Document Identifier**: SV-LIM-2026-V1  
**Project**: SentinelVault (Zero-Trust Privacy-Preserving Analytics Gateway)  
**Team**: HOTFIX (UG 59)  
**Date**: October 29, 2026  
**Status**: Factual & Transparent Engineering Disclosure

---

## 1. Purpose of this Document

In accordance with the SentinelVault Honest Completion Contract, we explicitly document all architectural boundaries, prototype constraints, and operational limitations. We do not claim that any software is bug-free or universally immune to attack.

---

## 2. Granular Limitations & Boundary Scope

### 2.1 Restricted Analytical Query Scope
- **Current Behavior**: SentinelVault intentionally restricts analytical query submission to single categorical `COUNT_DISTINCT` operations across allowlisted fields (e.g. `diagnosis_category = 'cardiovascular'`).
- **Rationale**: General SQL queries, continuous metric computations (`SUM`, `AVG`, `STDDEV`), and multi-table joins require complex bounded sensitivity calculations ($\Delta f$) that vary widely based on data distributions. Bounding sensitivity strictly to $\Delta f = 1.0$ guarantees mathematically sound Laplace noise addition without risk of under-perturbation.
- **Production Roadmap**: Implement clipping mechanisms and Gaussian $(\varepsilon, \delta)$-DP for continuous numerical metrics.

### 2.2 Demonstration Dataset Fixtures
- **Current Behavior**: The prototype executes against simulated JSON fixtures (`health_records_demo.json` with 500 patient encounters and `financial_transactions_demo.json` with 500 consumer banking transactions).
- **Rationale**: Isolates the gateway from external network dependencies and prevents accidental exposure of real private personal data during the hackathon.
- **Production Roadmap**: Add read-only connector adapters for Snowflake, Google BigQuery, and PostgreSQL.

### 2.3 Official Evaluation Harness Status
- **Current Behavior**: As reported by `GET /ready` and `GET /api/evaluation/status`, the official competition evaluation harness was not provided in the workspace (`evaluation_harness_status = "UNAVAILABLE"`).
- **Mitigation**: We built and executed an internal empirical benchmark (`utility_benchmark.py`) with 50 trials per parameter setting, validating that mathematical error bounds match theoretical Laplace distributions.

### 2.4 Cryptographic Key Management (HSM / KMS)
- **Current Behavior**: The Ed25519 private key used to sign Privacy Receipts and audit entries is generated and stored locally in `backend/keys/ed25519_audit_private.pem` with standard file permissions.
- **Production Roadmap**: In an enterprise production deployment, private signing keys should be delegated to a Hardware Security Module (HSM, PKCS#11) or Cloud KMS (AWS KMS, Google Cloud KMS, HashiCorp Vault) to protect keys from disk extraction.

### 2.5 Single-Gateway Rate Limiting
- **Current Behavior**: Network IP rate limits (30 requests per 60 seconds) are tracked in the local SQLite `rate_limits` table.
- **Production Roadmap**: In a distributed multi-gateway environment behind a load balancer, rate limits should be stored in a distributed in-memory cache (e.g. Redis / Memcached).

