# SentinelVault MVP — Known Limitations & Truthful Disclosures

**Project**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Tagline**: Analyze Data. Don't Expose It.  
**Team**: HOTFIX, Team ID UG 59  
**Track**: Privacy by Design — Unlock Data Without Exposing It  
**Date**: 2026-10-28  
**Document Classification**: Mandatory Anti-Fakery & Integrity Disclosure  

---

## 1. Principles of Truthful Disclosure

In strict compliance with our Anti-Fakery and Integrity Contract:
- SentinelVault **never** claims perfect security, zero data leakage, or guaranteed hackathon success.
- SentinelVault **never** substitutes hardcoded dummy values, fake progress delays, or non-functional UI buttons for real production logic.
- Implemented capabilities are clearly separated from unconfigured external resources.

---

## 2. Status of Official Competition Resources

| Component | Current Factual Status | Transparent Reason |
| :--- | :--- | :--- |
| **Official Accounting Specification** | `DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED` | The hackathon organizers have not yet released the official Track 4 advanced composition specification (e.g. Rényi DP, zCDP, or PLD accounting). SentinelVault implements discrete micro-epsilon integer accounting on SQLite. |
| **Official Empirical Risk & Attack Harness** | `OFFICIAL EMPIRICAL RISK EVALUATION NOT CONFIGURED` | Official re-identification and membership-inference attack test suites have not yet been distributed. SentinelVault discloses this status honestly via `/api/evaluation/status` and does not fabricate fake attack scores. |
| **Official Competition Datasets** | Clearly labelled synthetic demonstration fixtures | Synthetic fixtures (500 health records, 500 financial transactions) are provided for live demonstration and utility verification. They are never represented as official competition data. |

---

## 3. Technical & Architectural Limitations

### 3.1 Supported Analytical Operations
- **Supported in MVP**: `COUNT_DISTINCT_PRIVACY_UNITS` with equality predicates on approved categorical allowlists.
- **Not Supported in MVP**: Arbitrary SQL joins, freeform text filtering, floating-point aggregations (SUM/AVG), or grouping operations. Expanding to SUM/AVG requires bounded clipping ranges ($\Delta f = U - L$) which are slated for Phase 4.

### 3.2 Database Concurrency & Storage
- **Current Architecture**: Local SQLite with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) and `BEGIN IMMEDIATE` transaction locking.
- **Limitation**: While thread-safe and process-safe for local demonstrations and single-node instances, horizontal multi-node load balancing requires migrating to PostgreSQL with row-level locks (`SELECT ... FOR UPDATE`).

### 3.3 Differential Privacy Mechanism Scope
- **Mechanism**: Pure $\epsilon$-differential privacy via Laplace mechanism with non-negative integer rounding.
- **Sensitivity Assumption**: Global sensitivity $\Delta f = 1.0$ under distinct privacy unit deduplication. If a dataset lacks a clear privacy unit mapping, default sensitivity is conservative.
- **Limitation**: $(\epsilon, \delta)$-differential privacy with Gaussian noise or advanced composition is not active in the demonstration profile.

### 3.4 Cryptographic Key Management
- **Key Generation**: Ed25519 signing keypair is generated and stored locally in server memory/storage for the gateway instance.
- **Limitation**: In enterprise production, the private signing key should reside in a Hardware Security Module (HSM) or cloud KMS (e.g., Google Cloud KMS, AWS KMS) rather than on the filesystem.

