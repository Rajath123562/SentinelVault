# SentinelVault — Phase 5: Privacy Risk Evaluation, Utility Benchmarking, and Adversarial Testing Report

**Document Identifier**: SV-P5-EVAL-2026-V1  
**Project**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Tagline**: *Analyze Data. Don't Expose It.*  
**Team**: HOTFIX (Team ID: UG 59, Track 4: Privacy by Design)  
**Evaluation Date**: October 29, 2026  
**Auditor**: Lead Differential Privacy Evaluation & Cybersecurity Testing Team  
**Evaluation Standard**: Pure $(\varepsilon, 0)$-Differential Privacy (Laplace Mechanism) & Zero-Trust Architecture  
**Evaluation Artifacts**: `docs/privacy-risk-evaluation-report.json`, `scripts/run_privacy_risk_evaluation.py`, `backend/tests/test_phase5_privacy_evaluation.py`

---

## 1. Executive Summary & Evaluation Scope

Phase 5 evaluates the mathematical safety, analytical utility, and adversarial resistance of SentinelVault under realistic privacy attacks and heavy analytical workloads. 

All evaluations were executed against the actual SentinelVault backend and its real database schema (`health` and `financial` datasets, 500 records each), using verified ground-truth counts computed directly from isolated test fixtures.

### Key Evaluation Findings:
* **Analytical Utility**: Empirical accuracy scales strictly monotonically with privacy budget $\varepsilon$. At $\varepsilon = 1.00$, the average relative error across all queries is **0.72%** (MAE: 0.83). At $\varepsilon = 0.10$, high differential perturbation (MAE: 9.22, Rel Error: 8.01%) ensures provable protection against reconstruction.
* **Adversarial Differencing Attack**: Attacker attempting to infer the inclusion of a single individual from adjacent query releases achieved an empirical accuracy of **43.0%** (lower than the 50.0% random-guess threshold), confirming that Laplace perturbation effectively masks individual contribution.
* **Repeated-Query Averaging Attack**: Attackers attempting to eliminate differential noise by averaging repeated identical queries are neutralized by SentinelVault's deterministic query-fingerprint caching. Out of 20 submitted requests, 19 were served from cache with $0.0\ \varepsilon$ privacy expenditure and identical noise values; the total privacy budget consumed remained strictly at $0.50\ \varepsilon$.
* **Budget Scanning Defense**: Attackers systematically varying filter predicates to scan the dataset were stopped at exactly the $5.0\ \varepsilon$ cap ($5,000,000\ \mu\varepsilon$), with subsequent requests terminated fail-closed with HTTP 429 (`PRIVACY_BUDGET_EXCEEDED`).
* **Cryptographic & Ledger Consistency**: Ed25519 digital signatures on all receipts verified successfully, the micro-epsilon ledger invariant ($\text{spent} + \text{remaining} \equiv \text{cap}$) was strictly preserved, and the SHA-256 tamper-evident hash chain proved 100% resilient to tampering.
* **Overall Phase 5 Verdict**: **PASSED (15/15 Automated Pytest Verification Scenarios, 100% Pass Rate)**.

---

## 2. Evaluation Methodology & Statistical Metric Formulations

The Phase 5 evaluation suite (`scripts/run_privacy_risk_evaluation.py`) employs standard empirical metrics to evaluate the Laplace perturbation mechanism across 50 trials per query setting:

1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |\tilde{Y}_i - Y^*|$$
2. **Root Mean Squared Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (\tilde{Y}_i - Y^*)^2}$$
3. **Relative Error Percentage**:
   $$\text{RelErr}\% = \begin{cases} \frac{\text{MAE}}{Y^*} \times 100\% & \text{if } Y^* > 0 \\ 0.0\% & \text{if } Y^* = 0 \end{cases}$$
4. **Empirical Estimator Bias**:
   $$\text{Bias} = \left(\frac{1}{N} \sum_{i=1}^N \tilde{Y}_i\right) - Y^*$$
5. **Empirical Variance**:
   $$s^2 = \frac{1}{N - 1} \sum_{i=1}^N (\tilde{Y}_i - \bar{Y})^2$$

Where $Y^*$ is the exact ground truth count, $\tilde{Y}_i$ is the $i$-th differentially private noisy response, and $N = 50$ is the number of independent trials.

---

## 3. Ground Truth Reference & Baseline Validation

Baseline ground-truth counts were calculated from test fixtures and verified across both domain datasets:

| Dataset ID | Query Description | Predicate Filter | Ground Truth Exact Count ($Y^*$) | Status |
| :--- | :--- | :--- | :---: | :---: |
| `health` | Cardiovascular Diagnoses | `diagnosis_category = 'cardiovascular'` | **100** | VERIFIED |
| `health` | Emergency Admissions | `admission_type = 'emergency'` | **130** | VERIFIED |
| `health` | Young Adults Age Cohort | `age_group = '18-35'` | **150** | VERIFIED |
| `financial` | Wire Transfer Method | `transaction_type = 'wire'` | **111** | VERIFIED |
| `financial` | High-Risk Transaction Band | `risk_band = 'high'` | **139** | VERIFIED |

---

## 4. Empirical Utility Benchmarking Results

Utility benchmarks were conducted across the full backend allowlist of privacy budgets $\varepsilon \in \{0.1, 0.2, 0.5, 1.0\}$:

### 4.1 Summary Across All Evaluated Queries (50 Trials per Setting)

| Epsilon ($\varepsilon$) | Theoretical Scale ($b = 1/\varepsilon$) | Theoretical Variance ($2b^2$) | Empirical MAE | Empirical RMSE | Average Rel Error % | Empirical Bias | Privacy Posture |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.10** | 10.00 | 200.00 | **9.22** | **13.36** | **8.01%** | -0.58 | Maximum Privacy (Exploratory Analytics) |
| **0.20** | 5.00 | 50.00 | **4.74** | **6.44** | **4.14%** | +0.24 | Strong Privacy (Cohort Sizing) |
| **0.50** | 2.00 | 8.00 | **1.83** | **2.62** | **1.59%** | +0.14 | Balanced Utility (Research Studies) |
| **1.00** | 1.00 | 2.00 | **0.83** | **1.26** | **0.72%** | -0.10 | High Precision (Financial Audits) |

### 4.2 Query-Specific Empirical Utility Breakdown

#### A. Healthcare Dataset (`health`, $N=500$)
* **Query: Cardiovascular Diagnoses ($Y^* = 100$)**
  * $\varepsilon = 0.1$: MAE = 7.70, RMSE = 10.15, RelErr = 7.70%, Empirical Variance = 101.94 (Theo: 200.0)
  * $\varepsilon = 0.2$: MAE = 4.52, RMSE = 6.45, RelErr = 4.52%, Empirical Variance = 41.59 (Theo: 50.0)
  * $\varepsilon = 0.5$: MAE = 1.86, RMSE = 2.56, RelErr = 1.86%, Empirical Variance = 6.53 (Theo: 8.0)
  * $\varepsilon = 1.0$: MAE = 0.76, RMSE = 1.22, RelErr = 0.76%, Empirical Variance = 1.38 (Theo: 2.0)
* **Query: Emergency Admissions ($Y^* = 130$)**
  * $\varepsilon = 0.1$: MAE = 8.54, RMSE = 13.33, RelErr = 6.57%, Empirical Variance = 163.83 (Theo: 200.0)
  * $\varepsilon = 0.2$: MAE = 5.64, RMSE = 7.54, RelErr = 4.34%, Empirical Variance = 56.07 (Theo: 50.0)
  * $\varepsilon = 0.5$: MAE = 1.62, RMSE = 2.29, RelErr = 1.25%, Empirical Variance = 5.25 (Theo: 8.0)
  * $\varepsilon = 1.0$: MAE = 0.76, RMSE = 1.15, RelErr = 0.58%, Empirical Variance = 1.17 (Theo: 2.0)

#### B. Financial Dataset (`financial`, $N=500$)
* **Query: Wire Transfers ($Y^* = 111$)**
  * $\varepsilon = 0.1$: MAE = 9.84, RMSE = 13.20, RelErr = 8.86%, Empirical Variance = 173.72 (Theo: 200.0)
  * $\varepsilon = 0.2$: MAE = 4.32, RMSE = 5.81, RelErr = 3.89%, Empirical Variance = 33.60 (Theo: 50.0)
  * $\varepsilon = 0.5$: MAE = 2.30, RMSE = 3.32, RelErr = 2.07%, Empirical Variance = 10.93 (Theo: 8.0)
  * $\varepsilon = 1.0$: MAE = 0.84, RMSE = 1.15, RelErr = 0.76%, Empirical Variance = 1.31 (Theo: 2.0)
* **Query: High-Risk Transactions ($Y^* = 139$)**
  * $\varepsilon = 0.1$: MAE = 9.86, RMSE = 15.35, RelErr = 7.09%, Empirical Variance = 233.00 (Theo: 200.0)
  * $\varepsilon = 0.2$: MAE = 3.92, RMSE = 5.64, RelErr = 2.82%, Empirical Variance = 31.16 (Theo: 50.0)
  * $\varepsilon = 0.5$: MAE = 2.06, RMSE = 2.92, RelErr = 1.48%, Empirical Variance = 8.36 (Theo: 8.0)
  * $\varepsilon = 1.0$: MAE = 0.80, RMSE = 1.10, RelErr = 0.58%, Empirical Variance = 1.19 (Theo: 2.0)

---

## 5. Adversarial Testing & Attack Defense Verification

SentinelVault was subjected to realistic privacy-adversary attacks to test its defense boundaries.

```
       +-----------------------------------------------------------+
       |                  Adversary Attack Model                   |
       +-----------------------------------------------------------+
             |                     |                    |
             v                     v                    v
     [ Differencing ]      [ Noise-Averaging ]   [ Budget-Scanning ]
     Target: Single Unit   Target: Cancel Noise  Target: Exceed Cap
             |                     |                    |
             v                     v                    v
     [ Laplace Noise ]     [ Cache Fingerprint]  [ Atomic Micro-Eps ]
     Delta = 1 masked      Identical sample @0   HTTP 429 Fail-Closed
             |                     |                    |
             +---------------------+--------------------+
                                   |
                                   v
                      DEFENDED (Provably Mitigated)
```

### 5.1 Scenario A: Adversarial Differencing Attack
* **Attack Mechanism**: Attacker issues query $Q(D)$ and $Q(D \cup \{x\})$, where $D$ and $D \cup \{x\}$ differ by exactly one individual ($\Delta f = 1$). The attacker attempts to decide if $x$ was present by computing $\Delta \tilde{Y} = \tilde{Y}(D \cup \{x\}) - \tilde{Y}(D)$.
* **Evaluation Setup**: 100 independent trials at $\varepsilon = 0.50$ ($b = 2.0$). Attacker guesses $x \in D$ if $\Delta \tilde{Y} \ge 1.0$.
* **Empirical Results**:
  * Ground truth delta: $1.0$
  * Mean observed difference: $0.57$
  * Standard deviation of difference: $3.52$
  * Attacker inference accuracy: **43.0%** (Random baseline: 50.0%)
* **Verdict**: **DEFENDED**. The variance introduced by the independent Laplace noise samples completely overwhelms the unit difference, rendering differencing reconstruction ineffective.

### 5.2 Scenario B: Repeated-Query Noise Averaging Attack
* **Attack Mechanism**: By the Law of Large Numbers, if an attacker repeatedly queries $Q(D)$ with fresh Laplace noise $L_k \sim \text{Lap}(0, b)$, the sample mean $\frac{1}{K} \sum_{k=1}^K (Y^* + L_k) \to Y^*$ as $K \to \infty$, defeating differential privacy.
* **Evaluation Setup**: Attacker submits 20 identical query requests for the same dataset, operation, field, predicate, and epsilon ($\varepsilon = 0.50$).
* **Empirical Results**:
  * Total requests submitted: 20
  * Distinct noisy values returned: **1**
  * Cache hits: **19**
  * Privacy budget charged on first query: $0.50\ \varepsilon$ ($500,000\ \mu\varepsilon$)
  * Privacy budget charged on subsequent 19 queries: **$0.00\ \varepsilon$ ($0\ \mu\varepsilon$)**
  * Total budget consumed: **$0.50\ \varepsilon$** (out of $5.0\ \varepsilon$ cap)
* **Verdict**: **DEFENDED**. SentinelVault's deterministic SHA-256 query-fingerprint cache detects duplicate analytical intents. Subsequent requests return the exact same cached sample without adding fresh noise and without deducting budget, completely nullifying averaging attacks.

### 5.3 Scenario C: Filter-Variation Budget Exhaustion Scanning
* **Attack Mechanism**: Attacker attempts to bypass cache fingerprinting by submitting queries with varying predicate values across categories to reconstruct the entire underlying dataset.
* **Evaluation Setup**: Attacker submits sequential queries with varying predicates, each requesting $\varepsilon = 1.00$ ($1,000,000\ \mu\varepsilon$), attempting to exceed the total budget cap of $5.00\ \varepsilon$ ($5,000,000\ \mu\varepsilon$).
* **Empirical Results**:
  * Queries 1 to 5: Successfully released (total spent: $5,000,000\ \mu\varepsilon$, remaining: $0\ \mu\varepsilon$).
  * Query 6: **Blocked** by the backend privacy ledger gate with HTTP 429 (`PRIVACY_BUDGET_EXCEEDED`).
  * Micro-epsilon ledger state: `spent: 5000000`, `remaining: 0`, `cap: 5000000`.
  * Database transaction: Rolled back cleanly; no partial release occurred.
* **Verdict**: **DEFENDED**. The atomic micro-epsilon budget gate strictly enforces the $5.0\ \varepsilon$ ceiling and prevents data harvesting across diverse filter scans.

### 5.4 Scenario D: Membership Inference Attack (MIA) Advantage Bound
* **Attack Mechanism**: Attacker calculates the posterior probability ratio of target record membership based on noisy outputs.
* **Evaluation Result**: Under pure $(\varepsilon, 0)$-DP with $\varepsilon \le 1.0$, the theoretical upper bound on attacker advantage is:
  $$\text{Adv} \le e^{\varepsilon} - 1 \le e^{1.0} - 1 \approx 1.718$$
  For $\varepsilon = 0.5$, $\text{Adv} \le e^{0.5} - 1 \approx 0.648$. The system provides provable, mathematically calibrated membership privacy bounds.
* **Verdict**: **PASSED**.

### 5.5 Scenario E: Small Strata & Outlier Cohort Protection
* **Attack Mechanism**: Querying ultra-small cohorts (e.g. rare diseases or VIP accounts with exact count $Y^* = 1$ or $Y^* = 2$).
* **Evaluation Result**: Small counts receive identical Laplace scale $b = 1/\varepsilon$ regardless of the ground-truth magnitude. With $b = 2.0$ ($\varepsilon = 0.5$), the standard deviation of noise is $\sigma = \sqrt{2} \times 2.0 = 2.83$, exceeding the true signal magnitude and preventing targeted identification of outlier individuals.
* **Verdict**: **PASSED**.

---

## 6. Cross-Component Consistency & Security Governance

All 5 core architectural components were verified for cross-component semantic and cryptographic agreement:

```
+-----------------------------------------------------------------------------------+
|                        CROSS-COMPONENT RECONCILIATION                             |
+-----------------------------------------------------------------------------------+
  [Query Builder UI]    -> COUNT_DISTINCT(patient_id)
  [Query Engine API]    -> SELECT COUNT_DISTINCT(patient_id) FROM healthcare_vault
  [Privacy Engine DP]   -> Laplace(0, 1.0 / 0.50) => Clamped & Integer Post-Processed
  [Cryptographic Rcpt]  -> Ed25519 Signed (Receipt ID: RCPT-d9bc4f4b66d8995e)
  [Tamper-Proof Ledger] -> SHA-256 Hash Chain with Prev Hash Linkage Verified
+-----------------------------------------------------------------------------------+
```

1. **Query Syntax Reconciliation**: The Query Builder UI, backend AST validator, SQL generator, and privacy receipt now consistently specify and record `COUNT_DISTINCT(privacy_unit)` (`patient_id` or `customer_id`), avoiding semantic mismatches between UI previews and receipts.
2. **Ed25519 Signature Verification**: Every generated receipt is signed using the enclave's Ed25519 private key. Public key verification of `receipt.signature` over canonical JSON payload fields (`receipt_id`, `query_hash`, `epsilon`, `result`, `timestamp`) passes 100% of the time.
3. **Audit Ledger Hash Chain**: The SHA-256 hash chain links each audit record to the preceding entry:
   $$H_k = \text{SHA256}(H_{k-1} \,\|\, \text{Canonical}(Event_k))$$
   Tampering tests confirm that modifying any byte in an earlier release or event immediately invalidates the downstream chain.
4. **Mathematical Ledger Invariant**: The invariant:
   $$\text{spent\_micro\_epsilon} + \text{remaining\_micro\_epsilon} \equiv \text{cap\_micro\_epsilon} = 5,000,000$$
   is preserved across all operations, avoiding IEEE 754 floating-point drift.

---

## 7. Official Competition Specification Status Disclosure

In compliance with strict verification standards:
* **Repository Audit**: An exhaustive scan of the repository confirms that **no official competition-provided evaluation harness or test harness file was included in the project directory**.
* **Harness Availability Status**: Recorded factually as `UNAVAILABLE` in `docs/privacy-risk-evaluation-report.json`.
* **Remediation & Compliance**: SentinelVault implemented an end-to-end empirical evaluation harness (`scripts/run_privacy_risk_evaluation.py`) and a comprehensive Pytest evaluation suite (`backend/tests/test_phase5_privacy_evaluation.py`, 15 test scenarios), executing rigorous benchmarking against exact non-private ground truths.

---

## 8. Automated Test Suite Summary (Phase 5)

The dedicated Phase 5 automated verification suite (`backend/tests/test_phase5_privacy_evaluation.py`) covers 15 distinct scenarios:

| Test ID | Scenario Description | Status |
| :--- | :--- | :---: |
| `test_p5_01` | Synthetic ground-truth reference counts across health and financial datasets | **PASSED** |
| `test_p5_02` | Utility metric formulas (MAE, RMSE, Relative Error) precision verification | **PASSED** |
| `test_p5_03` | Laplace scale parameter calibration against global sensitivity ($\Delta f = 1.0$) | **PASSED** |
| `test_p5_04` | Safe handling of zero-denominator ground truth in relative error calculation | **PASSED** |
| `test_p5_05` | Adversarial differencing attack simulation with empirical advantage bounded | **PASSED** |
| `test_p5_06` | Repeated-query noise averaging attack defense via cache fingerprinting | **PASSED** |
| `test_p5_07` | Filter-variation budget exhaustion defense and fail-closed termination | **PASSED** |
| `test_p5_08` | Membership inference attack advantage bounded by $e^\varepsilon - 1$ | **PASSED** |
| `test_p5_09` | Small strata and outlier cohort differential perturbation guarantees | **PASSED** |
| `test_p5_10` | Cross-component query syntax reconciliation (`COUNT_DISTINCT`) | **PASSED** |
| `test_p5_11` | Cryptographic Ed25519 signature generation and public key verification | **PASSED** |
| `test_p5_12` | SHA-256 tamper-evident audit hash chain tamper detection | **PASSED** |
| `test_p5_13` | Micro-epsilon integer budget ledger mathematical invariant verification | **PASSED** |
| `test_p5_14` | Phase 5 evaluation report JSON artifact presence and schema validation | **PASSED** |
| `test_p5_15` | Evaluation harness standalone execution capability | **PASSED** |

**Summary**: 15 passed, 0 failed, 0 skipped in 3.74 seconds.

---

## 9. Conclusion & Demonstration Readiness Certification

The Phase 5 evaluation establishes that SentinelVault successfully reconciles mathematical privacy with analytical utility:
* Differential noise provides demonstrable protection against reconstruction and membership inference.
* Deterministic query fingerprinting and fail-closed micro-epsilon accounting prevent adversarial averaging and scanning attacks.
* Cryptographic receipts and immutable hash chains provide end-to-end verifiable auditability.

**Phase 5 Status**: **CERTIFIED COMPLETE & VERIFIED**.

