# SentinelVault — Master Differential Privacy & Accounting Verification Report

**Document Identifier**: SV-DP-2026-V1  
**Project**: SentinelVault (Zero-Trust Privacy-Preserving Analytics Gateway)  
**Team**: HOTFIX (UG 59)  
**Verification Date**: October 29, 2026  
**Auditor**: Senior Differential Privacy Specialist (Empirical Verification)  
**Standard**: Formal $(\varepsilon, 0)$-Differential Privacy (Dwork et al.)

---

## 1. Mathematical Formulation & Architecture

SentinelVault protects sensitive dataset records by guaranteeing $(\varepsilon, 0)$-Differential Privacy for analytical COUNT queries.

### 1.1 Global Sensitivity ($\Delta f$)
For COUNT queries over bounded datasets with protected subject identifier units (e.g. `patient_id` in health records, `customer_id` in financial transactions), an individual contributing any number of records contributes to the count at most once via `COUNT_DISTINCT`.
$$\Delta f = \max_{D, D': \|D \oplus D'\| = 1} |f(D) - f(D')| = 1.0$$

### 1.2 Laplace Noise Mechanism
The gateway samples random noise from the centered Laplace distribution $\text{Lap}(b)$ with scale parameter:
$$b = \frac{\Delta f}{\varepsilon} = \frac{1.0}{\varepsilon}$$
The noisy response is:
$$\tilde{Y} = \max(0, \lfloor Y + \text{Lap}(b) \rceil)$$
Where $\lfloor \cdot \rceil$ represents nearest-integer rounding, preserving integral count semantics via valid post-processing.

---

## 2. Empirical Utility vs. Privacy Trade-Off Benchmark

Benchmark executed across 50 trials per epsilon configuration using deterministic seed 42 (Report source: `docs/utility-benchmark-report.json`).

| Epsilon ($\varepsilon$) | Theoretical Scale ($b$) | Theoretical Std Dev ($\sigma$) | Empirical MAE | Empirical RMSE | Average Relative Error | Privacy Posture |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.10** | 10.00 | 14.14 | **9.09** | **12.60** | **8.42%** | Maximum Privacy (Exploratory Analytics) |
| **0.20** | 5.00 | 7.07 | **5.57** | **7.43** | **5.02%** | High Privacy (Standard Release) |
| **0.50** | 2.00 | 2.83 | **2.01** | **2.71** | **1.81%** | Balanced Utility (Clinical Studies) |
| **1.00** | 1.00 | 1.41 | **0.93** | **1.44** | **0.84%** | High Precision (Financial Audits) |

### Key Empirical Observations:
1. **Unbiased Estimator**: Mean empirical error across all tests is bounded within $|\bar{e}| < 0.25$, confirming zero systematic bias.
2. **Variance Monotonicity**: Noise variance strictly decreases as $\varepsilon$ increases, confirming the mathematical trade-off.
3. **Accuracy at $\varepsilon = 1.0$**: Average relative error is under 1.0%, providing accurate insights while preserving provable mathematical privacy.

---

## 3. Privacy Accounting & Micro-Epsilon Ledger

### 3.1 Integer Arithmetic (Zero Floating-Point Drift)
Floating-point arithmetic (e.g. IEEE 754 float addition) suffers from rounding drift over repeated calculations (e.g. $0.1 + 0.2 = 0.30000000000000004$). SentinelVault eliminates drift by tracking all expenditures in **integer micro-epsilons**:
$$1\ \varepsilon = 1,000,000\ \mu\varepsilon$$
- $\varepsilon = 0.1 \implies 100,000\ \mu\varepsilon$
- $\varepsilon = 0.2 \implies 200,000\ \mu\varepsilon$
- $\varepsilon = 0.5 \implies 500,000\ \mu\varepsilon$
- $\varepsilon = 1.0 \implies 1,000,000\ \mu\varepsilon$
- Maximum Budget Cap: $5.0\ \varepsilon = 5,000,000\ \mu\varepsilon$

### 3.2 Invariant Verification
Across all test suites, the invariant was verified:
$$\text{spent\_micro\_epsilon} + \text{remaining\_micro\_epsilon} \equiv \text{cap\_micro\_epsilon}$$
No negative remaining balance is possible. Over-budget requests fail closed with HTTP 429.

---

## 4. Query Re-Use Caching & Idempotency

SentinelVault prevents budget exhaustion from repeated identical queries by implementing canonical SHA-256 fingerprint caching:
1. When an analyst submits an identical query (`dataset_id`, `field`, `operator`, `value`, `epsilon`), the system retrieves the previously committed randomized result from `query_releases`.
2. The response is flagged with `is_cached: True` and incurs **$0.0\ \varepsilon$ privacy cost**.
3. This prevents reconstruction attacks and averts unnecessary privacy expenditure.

