"""Utility and Privacy Trade-off Empirical Benchmark for HOTFIX MVP.

Evaluates Laplace mechanism utility across multiple epsilon values:
- Epsilon values: [0.1, 0.2, 0.5, 1.0]
- 50 trials per epsilon
- Queries on synthetic health records
- Computes MAE, RMSE, and Relative Error against non-private exact baseline.
- Saves result to docs/utility-benchmark-report.json
"""

import sys
import os
import json
import math
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path so we can import app services
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.privacy_engine import apply_laplace_noise
from app.services.query_engine import _calculate_exact_count_internal


def run_benchmark():
    print("=" * 60)
    print("HOTFIX MVP: Differential Privacy Utility Benchmark Runner")
    print("=" * 60)

    dataset_id = "health"
    test_queries = [
        {"field": "diagnosis_category", "value": "cardiovascular", "label": "Cardiovascular Diagnoses"},
        {"field": "admission_type", "value": "emergency", "label": "Emergency Admissions"},
        {"field": "age_group", "value": "18-35", "label": "Young Adults (18-35)"},
    ]

    epsilons = [0.1, 0.2, 0.5, 1.0]
    num_trials = 50

    results = {
        "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_evaluated": dataset_id,
        "mechanism": "Laplace Mechanism (diffprivlib / CSPRNG)",
        "trials_per_setting": num_trials,
        "epsilons_tested": epsilons,
        "queries": [],
        "overall_summary_by_epsilon": {}
    }

    print(f"Dataset: {dataset_id}")
    print(f"Trials per setting: {num_trials}")
    print("-" * 60)

    for query in test_queries:
        field = query["field"]
        val = query["value"]
        label = query["label"]
        exact_count = _calculate_exact_count_internal(dataset_id, field, val)

        query_record = {
            "label": label,
            "field": field,
            "value": val,
            "exact_reference_count": exact_count,
            "evaluations": {}
        }

        print(f"\nQuery: {label} (Exact Count = {exact_count})")
        print(f"{'Epsilon':<10} | {'Mean Output':<14} | {'MAE':<10} | {'RMSE':<10} | {'Rel Error %':<12}")
        print("-" * 60)

        for eps in epsilons:
            noisy_counts = [apply_laplace_noise(exact_count, epsilon=eps) for _ in range(num_trials)]
            mean_output = sum(noisy_counts) / num_trials
            abs_errors = [abs(c - exact_count) for c in noisy_counts]
            sq_errors = [(c - exact_count) ** 2 for c in noisy_counts]

            mae = sum(abs_errors) / num_trials
            rmse = math.sqrt(sum(sq_errors) / num_trials)
            rel_err_pct = (mae / exact_count * 100.0) if exact_count > 0 else 0.0

            query_record["evaluations"][str(eps)] = {
                "epsilon": eps,
                "mean_noisy_output": round(mean_output, 2),
                "mae": round(mae, 2),
                "rmse": round(rmse, 2),
                "rel_error_pct": round(rel_err_pct, 2),
                "min_observed": min(noisy_counts),
                "max_observed": max(noisy_counts),
            }

            print(f"{eps:<10} | {mean_output:<14.2f} | {mae:<10.2f} | {rmse:<10.2f} | {rel_err_pct:<11.2f}%")

        results["queries"].append(query_record)

    # Compute overall average across all queries for each epsilon
    print("\n" + "=" * 60)
    print("OVERALL UTILITY VS PRIVACY SUMMARY")
    print("=" * 60)
    print(f"{'Epsilon':<10} | {'Avg MAE':<12} | {'Avg RMSE':<12} | {'Avg Rel Error %':<15}")
    print("-" * 60)

    for eps in epsilons:
        eps_key = str(eps)
        avg_mae = sum(q["evaluations"][eps_key]["mae"] for q in results["queries"]) / len(results["queries"])
        avg_rmse = sum(q["evaluations"][eps_key]["rmse"] for q in results["queries"]) / len(results["queries"])
        avg_rel_err = sum(q["evaluations"][eps_key]["rel_error_pct"] for q in results["queries"]) / len(results["queries"])

        results["overall_summary_by_epsilon"][eps_key] = {
            "avg_mae": round(avg_mae, 2),
            "avg_rmse": round(avg_rmse, 2),
            "avg_rel_error_pct": round(avg_rel_err, 2),
            "theoretical_stddev": round(math.sqrt(2.0) / eps, 2)
        }
        print(f"{eps:<10} | {avg_mae:<12.2f} | {avg_rmse:<12.2f} | {avg_rel_err:<14.2f}%")

    results["conclusions"] = [
        "Noise decreases inversely proportional to epsilon as expected from Laplace distribution scale b = 1/epsilon.",
        "At epsilon=1.0, mean relative error is lowest (high analytical utility).",
        "At epsilon=0.1, noise is highest providing strong plausible deniability at higher utility cost.",
        "Demonstration benchmark completed empirically on synthetic health records dataset."
    ]

    # Save to docs/utility-benchmark-report.json
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "utility-benchmark-report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Benchmark report saved to: {report_path}")
    return results


if __name__ == "__main__":
    run_benchmark()

