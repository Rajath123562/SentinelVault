# SentinelVault — Live Demonstration Readiness Report & Demo Script

**Document Identifier**: SV-DEMO-2026-V1  
**Project**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Team**: HOTFIX (UG 59)  
**Hackathon Track**: Track 4: Privacy by Design  
**Date**: October 29, 2026  
**Demonstration Status**: **100% READY FOR LIVE JUDGING DEMONSTRATION**

---

## 1. Pre-Configured Demonstration Accounts

| Role | Username | Password | Purpose in Demonstration |
| :--- | :--- | :--- | :--- |
| **Analyst** | `analyst_user` | `AnalystPass2026!` | Submits analytical queries, consumes privacy budget, inspects receipts. |
| **Data Steward** | `steward_user` | `StewardPass2026!` | Monitors dataset policies, reviews budget allowances, inspects security events. |
| **Auditor** | `auditor_user` | `AuditorPass2026!` | Inspects all issued receipts, runs cryptographic audit ledger hash chain verification. |
| **Administrator**| `admin_user` | `AdminPass2026!` | Manages user accounts, unlocks locked users, revokes compromised sessions. |

*Quick-Login Feature: Clicking any role pill on Screen 1 automatically populates the credentials for instantaneous demonstration.*

---

## 2. 5-Minute Live Judging Demonstration Script

### Step 1: The Zero-Trust Gateway Landing (Screen 1 & 15)
- **Action**: Open `http://localhost:5173/`.
- **Narration**: *"Welcome to SentinelVault by Team HOTFIX. Organizations have sensitive clinical and financial records they want to analyze, but traditional access grants either complete row exposure or coarse masks. SentinelVault solves this with a Zero-Trust Privacy-Preserving Analytics Gateway: Analyze Data. Don't Expose It."*
- **Visual**: Highlight the glowing cyber shield, animated mathematical wave SVG, and zero-trust authentication panel.

### Step 2: Analyst Query & Real Differential Privacy (Screens 2, 3 & 4)
- **Action**: Click the **Analyst** quick-fill button, sign in, click **Query Builder** in the sidebar.
- **Action**: Select **Synthetic Health Records**, field `diagnosis_category`, value `cardiovascular`.
- **Action**: Drag the **Privacy Loss Parameter ($\varepsilon$) slider** from 0.10 (High Privacy) to 0.50 (Balanced).
- **Narration**: *"Notice the live protected sandbox preview. The analyst cannot write arbitrary SQL or probe raw rows. The system enforces strict categorical allowlists and previews the exact differential privacy noise mechanism."*

### Step 3: Noise Injection & Cryptographic Privacy Receipts (Screens 5 & 7)
- **Action**: Click **Run Query**. A clean modal appears and delivers the noisy count.
- **Action**: Click **View Privacy Receipt**.
- **Narration**: *"The exact count was 100, but the analyst receives a noisy count (e.g. 102) mathematically perturbed by Laplace noise ($b = 2.0$). Furthermore, SentinelVault issues a cryptographically signed Privacy Receipt signed with an Ed25519 private key. This receipt proves data provenance, privacy expenditure, and policy conformance."*
- **Action**: Click **Verify Signature** (shows green checkmark).

### Step 4: Micro-Epsilon Accounting & Budget Ledger (Screen 6)
- **Action**: Navigate to **Privacy Budget**.
- **Narration**: *"To prevent reconstruction attacks, SentinelVault tracks cumulative privacy loss in integer micro-epsilons ($1\ \varepsilon = 1,000,000\ \mu\varepsilon$) with zero floating-point drift. When the 5.0 epsilon cap is reached, the gateway fails closed."*
- **Visual**: Show the interactive SVG donut chart and transaction consumption history.

### Step 5: Auditor Cryptographic Hash Chain Verification (Screen 8)
- **Action**: Log out and click the **Auditor** quick-fill button to log in. Navigate to **Audit Logs**.
- **Narration**: *"Auditors have independent oversight. Every query release is appended to an immutable SHA-256 hash chain anchored in our genesis block. If an insider modifies even a single byte in the database, the hash chain immediately breaks and flags tampering."*
- **Visual**: Show the `Chain Intact: Verified` badge and entry hashes.

### Step 6: SIEM Security Events & Defenses (Screen 9)
- **Action**: Navigate to **Security Events & Alerts**.
- **Narration**: *"Failed logins, policy violations, and rate-limiting triggers are streamed into an immutable security event log. Even if an attacker attempts username enumeration, constant-time dummy verification neutralizes timing side-channels."*

---

## 3. Clean-Start Verification Command

To run the entire platform from a clean start:
```powershell
# 1. Run all automated tests (takes ~90s)
powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1

# 2. Launch both backend & frontend daemons
powershell -ExecutionPolicy Bypass -File scripts/start_all.ps1
```
- Gateway API: `http://localhost:8000`
- Interactive Web App: `http://localhost:5173`

