"""
SentinelVault Database Backup, Verification, and Anti-Rollback Recovery Service.

Provides:
- Online transactionally consistent backups via SQLite backup API.
- SHA-256 cryptographic integrity checksums and sidecar metadata.
- Pre-restore and post-restore integrity and foreign key validation.
- Anti-rollback privacy budget reconciliation to prevent replay/re-spending of exhausted budgets.
- Cryptographic audit chain verification on restored databases.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.db.connection import get_db_path, get_connection
from app.services.crypto_audit import verify_audit_ledger, TRUSTED_KEY_ID

BACKUP_SCHEMA_VERSION = "1.0.0"


class BackupError(Exception):
    """Raised when backup creation or verification fails."""
    pass


class RestoreError(Exception):
    """Raised when database restoration fails or integrity check detects corruption."""
    pass


class BudgetInconsistencyError(RestoreError):
    """Raised when restored budget ledger exhibits rollback discrepancy against historical releases."""
    pass


def get_backup_dir() -> Path:
    """Resolves and ensures existence of the backup directory."""
    env_dir = os.getenv("HOTFIX_BACKUP_DIR", "backups")
    p = Path(env_dir)
    if p.is_absolute():
        p.mkdir(parents=True, exist_ok=True)
        return p
    if Path.cwd().name == "backend":
        target = Path.cwd() / p
    else:
        target = Path.cwd() / "backend" / p
    target.mkdir(parents=True, exist_ok=True)
    return target


def calculate_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file in chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_database_backup(
    source_db_path: Optional[Path] = None,
    destination_dir: Optional[Path] = None,
    label: str = "scheduled"
) -> Dict[str, Any]:
    """
    Creates an atomic, consistent online backup of the SQLite database.
    Uses sqlite3.Connection.backup() to ensure point-in-time consistency even under concurrent writes.
    Generates SHA-256 checksum and a JSON metadata sidecar.
    """
    source_path = Path(source_db_path) if source_db_path else get_db_path()
    if not source_path.exists():
        raise BackupError(f"Source database not found: {source_path}")

    dest_dir = Path(destination_dir) if destination_dir else get_backup_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand_token = secrets.token_hex(4)
    backup_id = f"BKP-{timestamp_str}-{rand_token}"
    
    backup_db_filename = f"sentinelvault_{backup_id}.db"
    backup_meta_filename = f"sentinelvault_{backup_id}.json"

    backup_db_path = dest_dir / backup_db_filename
    backup_meta_path = dest_dir / backup_meta_filename

    # Perform online atomic backup using SQLite API
    src_conn = sqlite3.connect(str(source_path), timeout=30.0)
    try:
        dest_conn = sqlite3.connect(str(backup_db_path), timeout=30.0)
        try:
            with dest_conn:
                src_conn.backup(dest_conn, pages=100)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()

    # Calculate checksum of backup artifact
    sha256_hash = calculate_file_sha256(backup_db_path)
    file_size = backup_db_path.stat().st_size

    # Inspect backup to compile authoritative metadata
    check_conn = sqlite3.connect(str(backup_db_path))
    check_conn.row_factory = sqlite3.Row
    try:
        # Integrity checks on backup
        integrity = check_conn.execute("PRAGMA integrity_check").fetchall()
        integrity_status = [r[0] for r in integrity]
        if integrity_status != ["ok"]:
            raise BackupError(f"Backup failed SQLite integrity check: {integrity_status}")

        # Gather table statistics
        stats: Dict[str, int] = {}
        for tbl in ["users", "budget_ledger", "query_releases", "privacy_receipts", "audit_log", "security_events", "security_alerts"]:
            try:
                row = check_conn.execute(f"SELECT COUNT(*) AS cnt FROM {tbl}").fetchone()
                stats[tbl] = row["cnt"] if row else 0
            except sqlite3.OperationalError:
                stats[tbl] = 0

        # Budget snapshot
        budgets = {}
        try:
            b_rows = check_conn.execute("SELECT dataset_id, cap_micro_epsilon, spent_micro_epsilon, remaining_micro_epsilon FROM budget_ledger").fetchall()
            for b in b_rows:
                budgets[b["dataset_id"]] = {
                    "cap_epsilon": b["cap_micro_epsilon"] / 1_000_000,
                    "spent_epsilon": b["spent_micro_epsilon"] / 1_000_000,
                    "remaining_epsilon": b["remaining_micro_epsilon"] / 1_000_000
                }
        except sqlite3.OperationalError:
            pass

        # Audit chain status
        audit_check = verify_audit_ledger(check_conn)
        audit_valid = audit_check.get("valid", False)
    finally:
        check_conn.close()

    metadata: Dict[str, Any] = {
        "backup_id": backup_id,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": BACKUP_SCHEMA_VERSION,
        "source_database": source_path.name,
        "backup_file": backup_db_filename,
        "file_size_bytes": file_size,
        "sha256_checksum": sha256_hash,
        "trusted_key_id": TRUSTED_KEY_ID,
        "table_counts": stats,
        "budget_ledger_snapshot": budgets,
        "audit_chain_valid": audit_valid,
        "status": "COMPLETED"
    }

    # Write metadata sidecar
    with open(backup_meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def verify_backup_integrity(
    backup_db_path: Path,
    expected_checksum: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifies that a backup file is mathematically and syntactically sound:
    1. File exists and has non-zero size.
    2. SHA-256 matches expected checksum (or sidecar metadata).
    3. PRAGMA integrity_check passes.
    4. PRAGMA foreign_key_check returns zero violations.
    5. Audit ledger chain is cryptographically intact.
    """
    p = Path(backup_db_path)
    if not p.exists():
        return {
            "valid": False,
            "error": f"Backup file not found: {p}",
            "checksum_match": False,
            "integrity_check_passed": False
        }

    actual_checksum = calculate_file_sha256(p)

    # Check sidecar if expected_checksum omitted
    if not expected_checksum:
        sidecar = p.with_suffix(".json")
        if sidecar.exists():
            try:
                with open(sidecar, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    expected_checksum = meta.get("sha256_checksum")
            except Exception:
                pass

    checksum_match = True
    if expected_checksum:
        checksum_match = (actual_checksum.lower() == expected_checksum.lower())
        if not checksum_match:
            return {
                "valid": False,
                "error": f"Checksum mismatch: expected {expected_checksum}, calculated {actual_checksum}",
                "checksum_match": False,
                "actual_checksum": actual_checksum,
                "integrity_check_passed": False
            }

    # Open read-only to verify database internals
    conn = sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        integrity_rows = conn.execute("PRAGMA integrity_check").fetchall()
        integrity_ok = [r[0] for r in integrity_rows] == ["ok"]

        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        fk_ok = (len(fk_violations) == 0)

        audit_result = verify_audit_ledger(conn)
        audit_ok = audit_result.get("valid", False)

        is_valid = checksum_match and integrity_ok and fk_ok and audit_ok
        return {
            "valid": is_valid,
            "file": p.name,
            "sha256_checksum": actual_checksum,
            "checksum_match": checksum_match,
            "integrity_check_passed": integrity_ok,
            "foreign_keys_valid": fk_ok,
            "audit_chain_valid": audit_ok,
            "audit_entries_verified": audit_result.get("verified_entries", 0),
            "error": None if is_valid else "Database integrity or audit chain validation failed."
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Failed inspecting backup database: {str(e)}",
            "checksum_match": checksum_match,
            "integrity_check_passed": False
        }
    finally:
        conn.close()


def restore_database_backup(
    backup_db_path: Path,
    target_db_path: Optional[Path] = None,
    verify_first: bool = True,
    auto_reconcile_budget: bool = True
) -> Dict[str, Any]:
    """
    Safely restores a database from a validated backup artifact:
    1. Pre-restore validation: aborts fail-closed if backup is corrupt or checksum fails.
    2. Atomic restoration to target database path.
    3. Anti-Rollback Budget Reconciliation:
       - Checks sum of historical releases in query_releases against spent_micro_epsilon in budget_ledger.
       - Disallows rolling back committed privacy expenditures.
       - Automatically reconciles budget to authoritative release totals.
    4. Post-restore cryptographic audit verification.
    """
    backup_path = Path(backup_db_path)
    if not backup_path.exists():
        raise RestoreError(f"Backup file does not exist: {backup_path}")

    # Step 1: Pre-restore verification
    if verify_first:
        v_res = verify_backup_integrity(backup_path)
        if not v_res["valid"]:
            raise RestoreError(f"Pre-restore integrity check failed: {v_res.get('error')}")

    target_path = Path(target_db_path) if target_db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Perform safe copy to target
    temp_target = target_path.with_suffix(".tmp_restore")
    shutil.copy2(str(backup_path), str(temp_target))

    # Reconcile budget and verify database before moving into live target
    reconciled_budgets: Dict[str, Any] = {}
    conn = sqlite3.connect(str(temp_target))
    conn.row_factory = sqlite3.Row
    try:
        # Check budget vs releases
        datasets = ["health", "financial"]
        for ds in datasets:
            # Sum releases
            rel_row = conn.execute(
                "SELECT COALESCE(SUM(epsilon_micro), 0) AS total_micro FROM query_releases WHERE dataset_id = ?",
                (ds,)
            ).fetchone()
            sum_releases_micro = rel_row["total_micro"] if rel_row else 0

            # Ledger row
            b_row = conn.execute(
                "SELECT cap_micro_epsilon, spent_micro_epsilon, remaining_micro_epsilon FROM budget_ledger WHERE dataset_id = ?",
                (ds,)
            ).fetchone()

            if b_row:
                cap_micro = b_row["cap_micro_epsilon"]
                spent_micro = b_row["spent_micro_epsilon"]
                remaining_micro = b_row["remaining_micro_epsilon"]

                # Detect rollback inconsistency
                is_inconsistent = (spent_micro < sum_releases_micro)
                if is_inconsistent:
                    if not auto_reconcile_budget:
                        raise BudgetInconsistencyError(
                            f"Rollback detected on dataset '{ds}': ledger shows {spent_micro} µε spent, "
                            f"but query_releases records {sum_releases_micro} µε historical expenditure."
                        )
                    # Anti-rollback reconciliation: force ledger to authoritative release total
                    corrected_spent = sum_releases_micro
                    corrected_remaining = max(0, cap_micro - corrected_spent)
                    now_iso = datetime.now(timezone.utc).isoformat()
                    conn.execute("""
                        UPDATE budget_ledger 
                        SET spent_micro_epsilon = ?, remaining_micro_epsilon = ?, updated_at = ?
                        WHERE dataset_id = ?
                    """, (corrected_spent, corrected_remaining, now_iso, ds))

                    reconciled_budgets[ds] = {
                        "status": "RECONCILED_ANTI_ROLLBACK",
                        "previous_spent_epsilon": spent_micro / 1_000_000,
                        "authoritative_spent_epsilon": corrected_spent / 1_000_000,
                        "remaining_epsilon": corrected_remaining / 1_000_000
                    }
                else:
                    reconciled_budgets[ds] = {
                        "status": "CONSISTENT",
                        "spent_epsilon": spent_micro / 1_000_000,
                        "remaining_epsilon": remaining_micro / 1_000_000
                    }

        conn.commit()

        # Audit chain check on restored database
        audit_check = verify_audit_ledger(conn)
        if not audit_check["valid"]:
            raise RestoreError(f"Restored database failed audit chain check: {audit_check.get('error_message')}")
    finally:
        conn.close()

    # Atomically replace live database
    if target_path.exists():
        # Keep immediate fallback
        safety_backup = target_path.with_suffix(".pre_restore_bak")
        shutil.move(str(target_path), str(safety_backup))

    shutil.move(str(temp_target), str(target_path))

    return {
        "status": "RESTORE_SUCCESSFUL",
        "target_database": str(target_path),
        "backup_source": str(backup_path),
        "audit_chain_valid": True,
        "budget_reconciliation": reconciled_budgets,
        "restored_at": datetime.now(timezone.utc).isoformat()
    }


def list_backups(destination_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns all backup files and parsed metadata sorted chronologically descending."""
    dest_dir = Path(destination_dir) if destination_dir else get_backup_dir()
    if not dest_dir.exists():
        return []

    backups = []
    for f in dest_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                meta = json.load(fp)
                backups.append(meta)
        except Exception:
            continue

    backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return backups
