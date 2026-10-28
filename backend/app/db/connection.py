"""SQLite database connection and schema initialization for HOTFIX MVP."""

import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import secrets

DB_PATH_ENV = os.getenv("HOTFIX_DB_PATH", "hotfix_mvp.db")


def get_db_path() -> Path:
    """Resolve database path relative to repository or backend directory."""
    p = Path(DB_PATH_ENV)
    if p.is_absolute():
        return p
    if Path.cwd().name == "backend":
        return Path.cwd() / p
    return Path.cwd() / "backend" / p


def get_connection() -> sqlite3.Connection:
    """Returns an active SQLite connection with row factory configured."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        timeout=30.0,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies a password against its PBKDF2 hash using constant-time comparison."""
    key, _ = hash_password(password, salt)
    return secrets.compare_digest(key, stored_hash)


def init_database() -> None:
    """Creates the SQLite tables and seeds the demo environment if not already initialized."""
    conn = get_connection()
    try:
        # Execute schema definition via executescript
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS budget_ledger (
            dataset_id TEXT PRIMARY KEY,
            cap_micro_epsilon INTEGER NOT NULL,
            spent_micro_epsilon INTEGER NOT NULL DEFAULT 0,
            remaining_micro_epsilon INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS query_releases (
            release_id TEXT PRIMARY KEY,
            idempotency_key TEXT UNIQUE,
            dataset_id TEXT NOT NULL,
            query_fingerprint TEXT NOT NULL,
            cache_key TEXT NOT NULL,
            epsilon_micro INTEGER NOT NULL,
            raw_count_internal INTEGER NOT NULL,
            noisy_count INTEGER NOT NULL,
            mechanism TEXT NOT NULL,
            user_id TEXT NOT NULL,
            receipt_id TEXT NOT NULL,
            is_cached_release INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_releases_cache_key ON query_releases(cache_key);

        CREATE TABLE IF NOT EXISTS privacy_receipts (
            receipt_id TEXT PRIMARY KEY,
            release_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            dataset_version TEXT NOT NULL,
            query_fingerprint TEXT NOT NULL,
            query_description TEXT NOT NULL,
            mechanism TEXT NOT NULL,
            epsilon_spent REAL NOT NULL,
            cumulative_epsilon REAL NOT NULL,
            remaining_budget REAL NOT NULL,
            policy_check_status TEXT NOT NULL,
            audit_entry_hash TEXT NOT NULL,
            signature TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (release_id) REFERENCES query_releases(release_id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            actor TEXT NOT NULL,
            dataset_scope TEXT NOT NULL,
            query_fingerprint TEXT NOT NULL,
            privacy_expenditure_micro INTEGER NOT NULL,
            cumulative_expenditure_micro INTEGER NOT NULL,
            mechanism TEXT NOT NULL,
            receipt_id TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            signature TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        # Seed default budget ledgers (5.0 Epsilon = 5,000,000 micro-epsilon)
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("""
        INSERT OR IGNORE INTO budget_ledger (dataset_id, cap_micro_epsilon, spent_micro_epsilon, remaining_micro_epsilon, updated_at)
        VALUES 
            ('health', 5000000, 0, 5000000, ?),
            ('financial', 5000000, 0, 5000000, ?);
        """, (now_iso, now_iso))

        # Seed demo users if not present
        demo_users = [
            ("analyst_user", os.getenv("DEMO_ANALYST_PASSWORD", "AnalystPass2026!"), "analyst"),
            ("steward_user", os.getenv("DEMO_STEWARD_PASSWORD", "StewardPass2026!"), "data_steward"),
            ("auditor_user", os.getenv("DEMO_AUDITOR_PASSWORD", "AuditorPass2026!"), "auditor"),
        ]
        for username, pwd, role in demo_users:
            existing = conn.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone()
            if not existing:
                h, salt = hash_password(pwd)
                conn.execute("""
                INSERT INTO users (username, password_hash, salt, role, failed_attempts, locked_until, created_at)
                VALUES (?, ?, ?, ?, 0, NULL, ?);
                """, (username, h, salt, role, now_iso))
        conn.commit()
    finally:
        conn.close()
