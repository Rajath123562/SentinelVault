# HOTFIX Security Architecture — Security Event Logging Catalog

**Project**: HOTFIX: Privacy-by-Design Analytics Gateway  
**Team ID**: UG 59  
**Domain**: Cybersecurity, Security Information and Event Management (SIEM), Audit Trails  
**Version**: 2.0.0-phase2  
**Status**: ACTIVE & VERIFIED  

---

## 1. Overview

HOTFIX maintains a dedicated, append-only security event ledger in SQLite (`security_events` table). This audit trail operates independently from the analytical differential-privacy hash chain, recording authentication attempts, privilege usage, session lifecycle events, network anomalies, and policy enforcement actions.

---

## 2. Security Events Schema

```sql
CREATE TABLE IF NOT EXISTS security_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    source_ip TEXT,
    resource TEXT,
    action TEXT,
    outcome TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_actor ON security_events(actor);
```

### Field Definitions

| Column | Type | Description |
| :--- | :--- | :--- |
| `event_id` | TEXT | Cryptographically unique identifier (`EVT-<24-hex-chars>`) |
| `event_type` | TEXT | Standardized category identifier (see Section 3) |
| `actor` | TEXT | Authenticated username, or `"anonymous"` for unauthenticated requests |
| `source_ip` | TEXT | IPv4/IPv6 address of the incoming client connection |
| `resource` | TEXT | Target entity (e.g. `session_for_analyst_user`, `receipt_RCT-1234`) |
| `action` | TEXT | Specific action attempted (e.g. `LOGIN`, `REVOKE`, `QUERY_EXECUTE`) |
| `outcome` | TEXT | Outcome status: `SUCCESS`, `FAILURE`, `DENIED`, `CHALLENGE` |
| `details` | TEXT | Structured textual contextual narrative describing the event |
| `timestamp` | TEXT | High-precision UTC timestamp formatted in ISO-8601 |

---

## 3. Catalog of Security Event Types

| Event Type | Typical Outcome | Trigger Condition | Severity |
| :--- | :---: | :--- | :---: |
| `LOGIN_SUCCESS` | `SUCCESS` | Correct password (and valid MFA if enabled) supplied | INFO |
| `LOGIN_FAILED` | `FAILURE` | Invalid password or nonexistent username attempted | WARNING |
| `ACCOUNT_LOCKED` | `FAILURE` / `DENIED` | Account reaches 5 consecutive failures, or login attempted while locked | HIGH |
| `MFA_REQUIRED` | `CHALLENGE` | First-factor credentials valid; second-factor TOTP challenge issued | INFO |
| `MFA_FAILED` | `FAILURE` | Invalid TOTP code or expired token provided | WARNING |
| `MFA_ENROLLED` | `SUCCESS` | User completes TOTP enrolment with valid confirmation code | INFO |
| `LOGOUT` | `SUCCESS` | User voluntarily terminates active session token | INFO |
| `SESSION_REVOKED` | `SUCCESS` | Administrative termination of session token by steward/admin | HIGH |
| `RATE_LIMITED` | `DENIED` | Source IP exceeds maximum permissible sliding-window request volume | HIGH |
| `POLICY_VIOLATION` | `DENIED` | Query submitted on non-allowlisted field or unauthorized dataset | WARNING |
| `PERMISSION_DENIED`| `DENIED` | Authenticated role attempts action without requisite RBAC permission | WARNING |

---

## 4. Access Governance & API Retrieval

### Endpoint
- **URL**: `GET /api/security/events`
- **Query Parameters**: `limit` (default: 50, min: 1, max: 200)
- **Required Permission**: `security.events.read`

### RBAC Enforcement
- **Data Steward (`data_steward`)**: ALLOWED.
- **Auditor (`auditor`)**: ALLOWED.
- **Admin (`admin`)**: ALLOWED.
- **Analyst (`analyst`)**: STRICTLY DENIED with **HTTP 403 Forbidden**.
- **Unauthenticated**: STRICTLY DENIED with **HTTP 401 Unauthorized**.

---

## 5. Security & Immutability Assurances

1. **Append-Only Operation**: Security events are inserted with unique IDs; no update or deletion endpoints are exposed across the public API.
2. **Forensic Integrity**: The ledger captures the actual actor, IP address, and timestamp for all security-relevant state transitions, providing reliable digital forensic evidence during incident reviews.

