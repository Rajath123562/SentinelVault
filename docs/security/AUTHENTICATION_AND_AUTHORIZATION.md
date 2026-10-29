# HOTFIX Security Architecture — Authentication and Authorization Specification

**Project**: HOTFIX: Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Domain**: Cybersecurity, Identity and Access Management (IAM), Privacy Engineering  
**Version**: 2.0.0-phase2  
**Status**: ACTIVE & VERIFIED  

---

## 1. Zero-Trust Architectural Principle

The HOTFIX gateway operates strictly under the **Zero-Trust Backend Enforcement Principle**:
1. **The browser and client application are entirely untrusted.** The frontend client is treated merely as a rendering surface and terminal input mechanism.
2. **The backend server is the sole authority** for identity resolution, credential verification, role assignment, permission authorization, rate limiting, and privacy-budget enforcement.
3. **No client-supplied roles, privileges, authorization flags, counter values, or bypass headers are ever accepted.**
4. Even if an adversary modifies frontend JavaScript state, alters `localStorage`, injects malicious HTTP headers, or interacts directly with the API via cURL/Postman, the backend enforces authorization rules identically and refuses access.

---

## 2. Authentication Architecture

### 2.1 Password Hashing & Storage
- **Algorithm**: PBKDF2 with HMAC-SHA256 (`hashlib.pbkdf2_hmac`).
- **Iteration Count**: 100,000 rounds.
- **Salt**: 16 bytes (32 hex characters) generated via `secrets.token_hex(16)`.
- **Comparison**: `secrets.compare_digest` constant-time verification to prevent timing attacks.

### 2.2 Side-Channel Prevention (Username Enumeration)
To prevent timing side-channels that disclose whether a username exists in the system:
- When an authentication request specifies a non-existent username, the backend executes `verify_dummy_password(password)` using a precomputed fixed dummy hash and salt.
- This guarantees that login requests for non-existent users undergo the identical 100,000 PBKDF2 iterations (~15–20 ms) as legitimate accounts, ensuring timing uniformity and defeating automated enumeration attacks.

---

## 3. Account Lockout Mechanism (Section 6.3)

To defeat credential stuffing and brute-force password guessing, HOTFIX implements an atomic server-side lockout mechanism:

| Parameter | Value | Enforcement |
| :--- | :--- | :--- |
| **Lockout Threshold** | 5 consecutive failed attempts | Server-side SQLite atomic transaction |
| **Lockout Duration** | 15 minutes (900 seconds) | Recorded as UTC ISO-8601 timestamp in `users.locked_until` |
| **State Reset** | On valid authentication | `failed_attempts` reset to 0, `locked_until` cleared |
| **Active Lockout Behavior** | HTTP 423 Locked | Even valid passwords fail while `now < locked_until` |
| **Durability** | Persistent | Survived across server restarts; stored in database |
| **Attempt Probing** | Non-extending | Probing during active lockout does not extend lockout end time |

---

## 4. Multi-Factor Authentication (RFC 6238 TOTP)

HOTFIX provides Time-based One-Time Password (TOTP) Multi-Factor Authentication:
- **Specification**: RFC 6238 standard TOTP.
- **Underlying Hash**: HMAC-SHA1 with dynamic truncation.
- **Time Step**: 30 seconds.
- **Clock Drift Tolerance**: $\pm 1$ step ($\pm 30$ seconds window).
-  **Secret Generation**: Cryptographically secure 20-byte Base32 string (`secrets.token_bytes(20)`).
- **URI Format**: Standard `otpauth://totp/HOTFIX:{username}?secret={secret}&issuer=HOTFIX-Gateway` compatible with Google Authenticator, Authy, and 1Password.
- **Recovery Codes**: 5 single-use 8-character hex recovery codes stored as SHA-256 hashes.
- **Enrolment Lifecycle**: 
  1. `POST /api/auth/mfa/enroll` generates secret in pending state.
  2. `POST /api/auth/mfa/verify` validates initial TOTP code before activating `mfa_enabled = 1`.
  3. Once activated, subsequent logins require `mfa_code` parameter; requests missing `mfa_code` receive HTTP 401 challenge.

---

## 5. Session Management & Lifecycle

- **Session Token**: 32 bytes (64 hex characters) generated via `secrets.token_hex(32)`, providing 256 bits of cryptographic entropy.
- **Session Duration**: 8 hours from creation.
- **Session State**: Tracked server-side in `sessions` table including `expires_at`, `last_accessed_at`, `is_revoked`, `ip_address`, and `user_agent`.
- **Voluntary Logout**: `POST /api/auth/logout` immediately invalidates the active token in the database.
- **Administrative Revocation**: `POST /api/auth/sessions/revoke` enables Data Stewards and Administrators to terminate any active session by token.
- **Revoked Token Rejection**: Any session with `is_revoked = 1` or deleted from `sessions` is strictly rejected with HTTP 401.

---

## 6. Role-Based Access Control (RBAC) & Granular Permissions

HOTFIX defines four distinct security roles with least-privilege permission mappings:

### 6.1 Role Definitions
1. **Analyst (`analyst`)**: Submits analytical count queries within approved allowlists, views own query releases and receipts, verifies public audit integrity. Cannot access raw records or administrative controls.
2. **Data Steward (`data_steward`)**: Manages dataset schemas, security policies, and active sessions; inspects all receipts; reviews security audit logs; revokes compromised sessions. Cannot execute analytical queries without steward authorization.
3. **Auditor (`auditor`)**: Inspects privacy receipts across all users, verifies cryptographic hash chains and Ed25519 signatures, inspects security event logs and system evaluation status. Cannot execute analytical queries or modify data.
4. **Admin (`admin`)**: Comprehensive administrative authority including user management and system configuration.

### 6.2 Granular Permissions Matrix

| Permission Identifier | Description | Analyst | Data Steward | Auditor | Admin |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `system.status.read` | View gateway health, readiness, and status | [x] | [x] | [x] | [x] |
| `dataset.metadata.read` | View approved dataset fields and categories | [x] | [x] | [x] | [x] |
| `dataset.query.execute` | Submit approved analytical queries with DP | [x] | [ ] | [ ] | [x] |
| `receipt.read.own` | View receipts created by own user session | [x] | [ ] | [ ] | [ ] |
| `receipt.read.authorized`| View any privacy receipt issued by gateway | [ ] | [x] | [x] | [x] |
| `audit.verify` | Cryptographically verify SHA-256 chain & signatures | [x] | [x] | [x] | [x] |
| `security.events.read` | Inspect security event audit logs | [ ] | [x] | [x] | [x] |
| `security.policy.manage`| Configure dataset policy and release parameters | [ ] | [x] | [ ] | [x] |
| `dataset.manage` | Onboard or retire datasets | [ ] | [x] | [ ] | [x] |
| `session.revoke` | Administratively terminate active sessions | [ ] | [x] | [ ] | [x] |
| `user.manage` | Create, lock, or modify user accounts | [ ] | [ ] | [ ] | [x] |

---

## 7. Object-Level Access Control (Privacy Receipts)

In addition to role-based access control, HOTFIX enforces **Resource/Object-Level Authorization**:
- Every Privacy Receipt records `user_id` designating the identity who generated the release.
- When an analyst calls `GET /api/receipts/{receipt_id}`, the backend checks `receipt.user_id == current_user.username`.
- If an analyst attempts to retrieve another analyst's receipt, access is denied with **HTTP 403 Forbidden**:
  `"Forbidden: Analysts may only view receipts they generated. Receipt '...' belongs to another analyst."`
- Privileged roles holding `receipt.read.authorized` (`data_steward`, `auditor`, `admin`) are permitted to inspect receipts globally for governance and compliance audits.

