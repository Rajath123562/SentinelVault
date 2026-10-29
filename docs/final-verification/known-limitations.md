# SentinelVault Known Limitations & Transparent Engineering Disclosures

**Product**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Team**: HOTFIX (Team ID: UG 59)  
**Track**: Track 4 — Privacy by Design  
**Date**: October 28, 2026  

---

## 1. Engineering Honesty Contract

In accordance with the Anti-Fakery and Honest Completion Contract, SentinelVault does not simulate, fake, or exaggerate any capability. All verified claims are backed by raw code and reproducible terminal evidence. The following architectural boundaries and limitations represent genuine engineering constraints of this minimum viable product (MVP):

---

## 2. Documented Scope Limitations

### 1. Official Track 4 Evaluation Harness Integration
- **Current State**: Demonstration accounting is active and enforced using exact micro-epsilon integer calculations ($1\ \epsilon = 1,000,000\ \mu\epsilon$).
- **Limitation**: Official competition specification conformance and synthetic adversary benchmarks remain unverified pending integration of the official Track 4 external testing harness. The gateway reports this honestly via `/api/system/status` and `/api/evaluation/status`.

### 2. Demonstration Database Engine
- **Current State**: Uses SQLite with Write-Ahead Logging (WAL) and file locking for local persistence (`backend/hotfix_mvp.db`).
- **Limitation**: While thread-safe for local prototype judging and concurrent test suites, enterprise production deployment requires migrating to a distributed transactional database (e.g., PostgreSQL with connection pooling) to support multi-region replicas.

### 3. Local Asymmetric Keypair Storage
- **Current State**: Cryptographic Ed25519 private key is held in memory and seeded securely on startup for digital signature generation.
- **Limitation**: In a production enterprise deployment, the signing key must be managed via a hardware security module (HSM) or cloud KMS (e.g., AWS KMS / GCP Cloud KMS) rather than environment variables or filesystem keys.

### 4. Query Grammar Expressiveness
- **Current State**: Strict allowlist grammar restricted to aggregate operations (`COUNT`, `COUNT DISTINCT`) over approved category columns.
- **Limitation**: Non-aggregate statistical analytics, arbitrary complex JOINs across non-isolated tables, and user-defined functions (UDFs) are deliberately rejected to mathematically guarantee bounded global sensitivity ($\Delta f = 1.0$) and prevent privacy leakage.

