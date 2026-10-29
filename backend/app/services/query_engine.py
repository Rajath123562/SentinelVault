"""Restricted analytical query execution, budget reservation, and atomic caching."""

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from app.db.connection import get_connection, record_security_event_db
from app.services.crypto_audit import (
    append_audit_entry,
    compute_receipt_hash,
    sign_entry_hash,
    TRUSTED_KEY_ID,
    RECEIPT_SCHEMA_VERSION,
)
from app.services.incident_service import (
    get_incident_status,
    STATE_RELEASES_DISABLED,
    STATE_RESTRICTED,
    ReleaseBlockedByIncidentError,
)
from app.services.privacy_engine import (
    apply_laplace_noise,
    EPSILON_ALLOWLIST,
    MECHANISM_NAME,
    DEMO_ACCOUNTING_NOTICE,
)

DATA_DIR = Path(os.getenv("HOTFIX_DATA_DIR", "backend/data"))
if not DATA_DIR.is_absolute() and Path.cwd().name == "backend":
    DATA_DIR = Path.cwd() / "data"


class PolicyViolationError(ValueError):
    """Raised when a query violates dataset allowlists or syntax boundaries."""
    pass


class BudgetExhaustedError(RuntimeError):
    """Raised when the cumulative privacy budget is insufficient."""
    pass


def _resolve_data_file(filename: str) -> Path:
    candidates = [
        DATA_DIR / filename,
        Path.cwd() / "backend" / "data" / filename,
        Path.cwd() / "data" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Dataset fixture not found: {filename}")


def get_dataset_metadata(dataset_id: str) -> Dict[str, Any]:
    """Loads dataset configuration and schema summary."""
    norm_id = (dataset_id or "").strip().lower()
    if norm_id not in {"health", "financial"}:
        raise PolicyViolationError(f"Unauthorized or unknown dataset: '{dataset_id}'")
    filename = "health_records_demo.json" if norm_id == "health" else "financial_transactions_demo.json"
    path = _resolve_data_file(filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "dataset_id": data["dataset_id"],
        "title": data["title"],
        "version": data["version"],
        "is_official_dataset": data["is_official_dataset"],
        "privacy_unit": data["privacy_unit"],
        "description": data["description"],
        "approved_fields": data["approved_fields"],
        "total_records": data["total_records"]
    }


def list_available_datasets() -> list[Dict[str, Any]]:
    """Returns summaries of all configured datasets."""
    return [
        get_dataset_metadata("health"),
        get_dataset_metadata("financial"),
    ]


def compute_query_fingerprint(dataset_id: str, field: str, operator: str, value: str) -> str:
    """Computes a canonical SHA-256 fingerprint for the query."""
    norm_op = "equals" if operator.strip().lower() in {"equals", "="} else operator.strip().lower()
    normalized = f"{dataset_id.strip().lower()}:{field.strip().lower()}:{norm_op}:{str(value).strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_cache_key(dataset_id: str, fingerprint: str, epsilon: float, mechanism: str) -> str:
    """Forms the release cache identity including dataset, query, epsilon, and mechanism."""
    return f"{dataset_id}:{fingerprint}:{epsilon:.4f}:{mechanism}"


def validate_query(dataset_id: str, field: str, operator: str, value: Any, epsilon: float) -> Dict[str, Any]:
    """Validates the query against strict allowlists."""
    if dataset_id not in {"health", "financial"}:
        raise PolicyViolationError(f"Unauthorized or unknown dataset: {dataset_id}")

    meta = get_dataset_metadata(dataset_id)
    approved_fields = meta["approved_fields"]

    if field not in approved_fields:
        raise PolicyViolationError(
            f"Field '{field}' is not in approved allowlist for dataset '{dataset_id}'. Approved: {list(approved_fields.keys())}"
        )

    norm_op = "equals" if str(operator).strip().lower() in {"equals", "="} else str(operator).strip().lower()
    if norm_op != "equals":
        raise PolicyViolationError(f"Unsupported operator '{operator}'. MVP strictly supports 'equals'.")

    allowed_values = approved_fields[field]
    if str(value).lower() not in [v.lower() for v in allowed_values]:
        raise PolicyViolationError(
            f"Value '{value}' is not an approved category for '{field}'. Allowed: {allowed_values}"
        )

    if epsilon not in EPSILON_ALLOWLIST:
        raise PolicyViolationError(
            f"Requested epsilon {epsilon} not permitted. Allowed: {sorted(list(EPSILON_ALLOWLIST))}"
        )

    return meta


def _calculate_exact_count_internal(dataset_id: str, field: str, value: str) -> int:
    """
    Computes exact count of distinct protected privacy units.
    Ensures that an individual contributing multiple records contributes at most once.
    This value is strictly internal and never exposed to analysts.
    """
    filename = "health_records_demo.json" if dataset_id == "health" else "financial_transactions_demo.json"
    path = _resolve_data_file(filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    privacy_unit = data["privacy_unit"]
    matching_units = set()

    val_str = str(value).lower()
    for row in data["records"]:
        row_val = str(row.get(field, "")).lower()
        if row_val == val_str:
            unit_id = row.get(privacy_unit)
            if unit_id:
                matching_units.add(unit_id)

    return len(matching_units)


def execute_query_pipeline(
    user_id: str,
    user_role: str,
    dataset_id: str,
    field: str,
    operator: str,
    value: Any,
    epsilon: float,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end atomic query release pipeline:
    Validate -> Check Idempotency/Cache -> Check Budget -> Laplace Noise -> Commit & Audit -> Receipt
    """
    # 1. Authorization check
    if user_role not in {"analyst", "auditor", "data_steward"}:
        raise PermissionError(f"Role '{user_role}' is not authorized to submit queries")

    # 2. Query validation
    try:
        meta = validate_query(dataset_id, field, operator, value, epsilon)
    except PolicyViolationError as e:
        conn_viol = get_connection()
        try:
            with conn_viol:
                record_security_event_db(
                    conn_viol,
                    event_type="POLICY_VIOLATION",
                    outcome="POLICY_VIOLATION",
                    actor=user_id,
                    resource=dataset_id,
                    action="QUERY_VALIDATE",
                    details=str(e)
                )
        finally:
            conn_viol.close()
        raise

    # Check Incident Response status fail-closed
    inc_status = get_incident_status()
    if not inc_status["releases_allowed"]:
        raise ReleaseBlockedByIncidentError(
            f"Privacy releases suspended fail-closed under active incident state '{inc_status['current_state']}': {inc_status['reason']}"
        )
    if inc_status["current_state"] == STATE_RESTRICTED and epsilon > inc_status["max_permitted_epsilon"]:
        raise PolicyViolationError(
            f"Gateway is operating in RESTRICTED incident state: maximum allowed epsilon is {inc_status['max_permitted_epsilon']}. Requested: {epsilon}."
        )

    fingerprint = compute_query_fingerprint(dataset_id, field, operator, str(value))
    cache_key = compute_cache_key(dataset_id, fingerprint, epsilon, MECHANISM_NAME)
    epsilon_micro = int(round(epsilon * 1_000_000))
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        # Atomic transaction: serialize budget-sensitive operations
        conn.execute("BEGIN IMMEDIATE;")

        # 3. Check idempotency key if provided
        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM query_releases WHERE idempotency_key = ?",
                (idempotency_key,)
            ).fetchone()
            if existing:
                receipt = conn.execute(
                    "SELECT * FROM privacy_receipts WHERE receipt_id = ?",
                    (existing["receipt_id"],)
                ).fetchone()
                conn.commit()
                return {
                    "release_id": existing["release_id"],
                    "noisy_count": existing["noisy_count"],
                    "epsilon_spent": 0.0,
                    "cumulative_epsilon": receipt["cumulative_epsilon"],
                    "remaining_budget": receipt["remaining_budget"],
                    "is_cached": True,
                    "policy_check_status": "POLICY_CHECK_PASSED",
                    "receipt": dict(receipt)
                }

        # 4. Repeated-query caching: Check if identical release exists
        cached_release = conn.execute(
            "SELECT * FROM query_releases WHERE cache_key = ? ORDER BY created_at DESC LIMIT 1",
            (cache_key,)
        ).fetchone()

        if cached_release:
            # Reusing previously committed randomized release at zero additional budget cost
            receipt = conn.execute(
                "SELECT * FROM privacy_receipts WHERE receipt_id = ?",
                (cached_release["receipt_id"],)
            ).fetchone()
            conn.commit()
            return {
                "release_id": cached_release["release_id"],
                "noisy_count": cached_release["noisy_count"],
                "epsilon_spent": 0.0,
                "cumulative_epsilon": receipt["cumulative_epsilon"],
                "remaining_budget": receipt["remaining_budget"],
                "is_cached": True,
                "policy_check_status": "POLICY_CHECK_PASSED",
                "receipt": dict(receipt)
            }

        # 5. Check and reserve budget
        budget_row = conn.execute(
            "SELECT spent_micro_epsilon, remaining_micro_epsilon, cap_micro_epsilon FROM budget_ledger WHERE dataset_id = ?",
            (dataset_id,)
        ).fetchone()

        if not budget_row:
            raise RuntimeError(f"Budget ledger not initialized for dataset: {dataset_id}")

        if budget_row["remaining_micro_epsilon"] < epsilon_micro:
            record_security_event_db(
                conn,
                event_type="BUDGET_EXHAUSTION_ATTEMPT",
                outcome="BUDGET_EXHAUSTED",
                actor=user_id,
                source_ip="internal",
                resource=dataset_id,
                action="QUERY_EXECUTE",
                details=f"Requested epsilon {epsilon} exceeds available allowance {budget_row['remaining_micro_epsilon'] / 1_000_000:.2f}"
            )
            conn.commit()
            raise BudgetExhaustedError(
                f"Privacy budget exhausted for dataset '{dataset_id}'. "
                f"Requested epsilon {epsilon} exceeds available allowance {budget_row['remaining_micro_epsilon'] / 1_000_000:.2f}."
            )

        # 6. Compute exact count internally and apply Laplace mechanism
        exact_count = _calculate_exact_count_internal(dataset_id, field, str(value))
        noisy_count = apply_laplace_noise(exact_count, epsilon)

        # 7. Update budget ledger
        new_spent_micro = budget_row["spent_micro_epsilon"] + epsilon_micro
        new_remaining_micro = budget_row["remaining_micro_epsilon"] - epsilon_micro

        conn.execute("""
        UPDATE budget_ledger 
        SET spent_micro_epsilon = ?, remaining_micro_epsilon = ?, updated_at = ?
        WHERE dataset_id = ?;
        """, (new_spent_micro, new_remaining_micro, now_iso, dataset_id))

        # 8. Create IDs
        release_id = f"REL-{secrets.token_hex(8)}"
        receipt_id = f"RCPT-{secrets.token_hex(8)}"
        event_id = f"EVT-{secrets.token_hex(8)}"
        query_desc = f"COUNT_DISTINCT({meta['privacy_unit']}) WHERE {field} = '{value}'"

        # 9. Append to hash-chained audit ledger
        entry_hash, signature = append_audit_entry(
            conn=conn,
            event_id=event_id,
            actor=user_id,
            dataset_scope=dataset_id,
            query_fingerprint=fingerprint,
            expenditure_micro=epsilon_micro,
            cumulative_micro=new_spent_micro,
            mechanism=MECHANISM_NAME,
            receipt_id=receipt_id,
            created_at=now_iso
        )

        # 10. Persist query release
        conn.execute("""
        INSERT INTO query_releases (
            release_id, idempotency_key, dataset_id, query_fingerprint,
            cache_key, epsilon_micro, raw_count_internal, noisy_count,
            mechanism, user_id, receipt_id, is_cached_release, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
        """, (
            release_id, idempotency_key, dataset_id, fingerprint,
            cache_key, epsilon_micro, exact_count, noisy_count,
            MECHANISM_NAME, user_id, receipt_id, now_iso
        ))

        # 11. Persist Privacy Receipt with Canonical Hash and Ed25519 Enclave Signature
        receipt_data = {
            "receipt_id": receipt_id,
            "release_id": release_id,
            "user_id": user_id,
            "dataset_id": dataset_id,
            "dataset_version": meta["version"],
            "query_fingerprint": fingerprint,
            "query_description": query_desc,
            "mechanism": MECHANISM_NAME,
            "epsilon_spent": epsilon,
            "cumulative_epsilon": new_spent_micro / 1_000_000,
            "remaining_budget": new_remaining_micro / 1_000_000,
            "policy_check_status": "POLICY_CHECK_PASSED",
            "audit_entry_hash": entry_hash,
            "key_id": TRUSTED_KEY_ID,
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "is_revoked": 0,
            "timestamp": now_iso
        }
        receipt_hash = compute_receipt_hash(receipt_data)
        receipt_data["receipt_hash"] = receipt_hash
        receipt_data["signature"] = signature

        conn.execute("""
        INSERT INTO privacy_receipts (
            receipt_id, release_id, user_id, dataset_id, dataset_version,
            query_fingerprint, query_description, mechanism, epsilon_spent,
            cumulative_epsilon, remaining_budget, policy_check_status,
            audit_entry_hash, receipt_hash, signature, key_id, schema_version,
            is_revoked, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
        """, (
            receipt_data["receipt_id"], receipt_data["release_id"], receipt_data["user_id"],
            receipt_data["dataset_id"], receipt_data["dataset_version"],
            receipt_data["query_fingerprint"], receipt_data["query_description"],
            receipt_data["mechanism"], receipt_data["epsilon_spent"],
            receipt_data["cumulative_epsilon"], receipt_data["remaining_budget"],
            receipt_data["policy_check_status"], receipt_data["audit_entry_hash"],
            receipt_data["receipt_hash"], receipt_data["signature"],
            receipt_data["key_id"], receipt_data["schema_version"],
            receipt_data["timestamp"]
        ))

        # Commit transaction
        conn.commit()

        return {
            "release_id": release_id,
            "noisy_count": noisy_count,
            "epsilon_spent": epsilon,
            "cumulative_epsilon": receipt_data["cumulative_epsilon"],
            "remaining_budget": receipt_data["remaining_budget"],
            "is_cached": False,
            "policy_check_status": "POLICY_CHECK_PASSED",
            "receipt": receipt_data
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_budget_status(dataset_id: str) -> Dict[str, Any]:
    """Retrieves authoritative budget information for a dataset."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT cap_micro_epsilon, spent_micro_epsilon, remaining_micro_epsilon, updated_at FROM budget_ledger WHERE dataset_id = ?",
            (dataset_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"Dataset '{dataset_id}' not found in budget ledger")

        cap = row["cap_micro_epsilon"] / 1_000_000
        spent = row["spent_micro_epsilon"] / 1_000_000
        remaining = row["remaining_micro_epsilon"] / 1_000_000

        # Retrieve recent releases to guarantee ledger reconciliation in frontend
        recent_rows = conn.execute("""
            SELECT release_id, query_description, epsilon_spent, cumulative_epsilon, timestamp
            FROM privacy_receipts
            WHERE dataset_id = ?
            ORDER BY timestamp DESC
            LIMIT 10;
        """, (dataset_id,)).fetchall()

        recent_releases = [
            {
                "release_id": r["release_id"],
                "query_description": r["query_description"],
                "epsilon_spent": r["epsilon_spent"],
                "cumulative_epsilon": r["cumulative_epsilon"],
                "timestamp": r["timestamp"]
            }
            for r in recent_rows
        ]

        return {
            "dataset_id": dataset_id,
            "cap_epsilon": cap,
            "spent_epsilon": spent,
            "remaining_epsilon": remaining,
            "accounting_notice": DEMO_ACCOUNTING_NOTICE,
            "updated_at": row["updated_at"],
            "recent_releases": recent_releases
        }
    finally:
        conn.close()

