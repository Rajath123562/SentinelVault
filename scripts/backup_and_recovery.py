#!/usr/bin/env python3
"""
SentinelVault Command-Line Backup & Disaster Recovery Utility.

Usage:
  python scripts/backup_and_recovery.py create [--label <name>] [--dest <dir>]
  python scripts/backup_and_recovery.py verify --file <path_to_db>
  python scripts/backup_and_recovery.py restore --file <path_to_db> [--target <target_db>]
  python scripts/backup_and_recovery.py list
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.backup_service import (
    create_database_backup,
    verify_backup_integrity,
    restore_database_backup,
    list_backups,
    BackupError,
    RestoreError,
    BudgetInconsistencyError,
)


def main():
    parser = argparse.ArgumentParser(description="SentinelVault Backup & Disaster Recovery CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: create
    create_parser = subparsers.add_parser("create", help="Create an atomic online database backup")
    create_parser.add_argument("--label", default="manual", help="Descriptive label for the backup")
    create_parser.add_argument("--dest", default=None, help="Destination directory for backup files")

    # Subcommand: verify
    verify_parser = subparsers.add_parser("verify", help="Verify backup integrity, checksum, and audit chain")
    verify_parser.add_argument("--file", required=True, help="Path to backup SQLite .db file")
    verify_parser.add_argument("--checksum", default=None, help="Expected SHA-256 checksum (optional)")

    # Subcommand: restore
    restore_parser = subparsers.add_parser("restore", help="Restore database with anti-rollback privacy reconciliation")
    restore_parser.add_argument("--file", required=True, help="Path to backup SQLite .db file")
    restore_parser.add_argument("--target", default=None, help="Target database path (optional)")
    restore_parser.add_argument("--no-verify", action="store_true", help="Skip pre-restore verification")
    restore_parser.add_argument("--no-reconcile", action="store_true", help="Disallow auto budget reconciliation")

    # Subcommand: list
    list_parser = subparsers.add_parser("list", help="List all available backups in the backup directory")
    list_parser.add_argument("--dir", default=None, help="Directory to search (optional)")

    args = parser.parse_args()

    if args.command == "create":
        dest = Path(args.dest) if args.dest else None
        try:
            meta = create_database_backup(destination_dir=dest, label=args.label)
            print(f"[SUCCESS] Backup created successfully: {meta['backup_id']}")
            print(f"  Artifact:  {meta['backup_file']}")
            print(f"  Checksum:  {meta['sha256_checksum']}")
            print(f"  Releases:  {meta['table_counts'].get('query_releases', 0)}")
            print(f"  Audit Log: {meta['table_counts'].get('audit_log', 0)} entries (Valid: {meta['audit_chain_valid']})")
            return 0
        except BackupError as e:
            print(f"[ERROR] Backup creation failed: {e}", file=sys.stderr)
            return 1

    elif args.command == "verify":
        p = Path(args.file)
        result = verify_backup_integrity(p, expected_checksum=args.checksum)
        if result["valid"]:
            print(f"[PASS] Backup integrity verified: {p.name}")
            print(f"  SHA-256:             {result['sha256_checksum']}")
            print(f"  Checksum Match:      {result['checksum_match']}")
            print(f"  SQLite Integrity:    {result['integrity_check_passed']}")
            print(f"  Foreign Keys:        {result['foreign_keys_valid']}")
            print(f"  Audit Chain Valid:   {result['audit_chain_valid']} ({result.get('audit_entries_verified', 0)} verified entries)")
            return 0
        else:
            print(f"[FAIL] Backup integrity check failed: {result.get('error')}", file=sys.stderr)
            return 1

    elif args.command == "restore":
        p = Path(args.file)
        target = Path(args.target) if args.target else None
        try:
            res = restore_database_backup(
                p,
                target_db_path=target,
                verify_first=not args.no_verify,
                auto_reconcile_budget=not args.no_reconcile
            )
            print(f"[SUCCESS] Database restored to: {res['target_database']}")
            print(f"  Audit Chain: Valid")
            print(f"  Budget Reconciliation:")
            for ds, bdata in res["budget_reconciliation"].items():
                print(f"    - {ds}: {bdata['status']} (Remaining: {bdata.get('remaining_epsilon', 0)} epsilon)")
            return 0
        except RestoreError as e:
            print(f"[ERROR] Restore failed: {e}", file=sys.stderr)
            return 1

    elif args.command == "list":
        b_dir = Path(args.dir) if args.dir else None
        backups = list_backups(destination_dir=b_dir)
        print(f"Found {len(backups)} backup(s):")
        for b in backups:
            print(f"  [{b.get('created_at')}] {b.get('backup_id')} ({b.get('file_size_bytes', 0)} bytes) - Audit Valid: {b.get('audit_chain_valid')}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
