"""Cryptographic Audit Trail and Ed25519 Signatures for HOTFIX."""

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

GENESIS_HASH = hashlib.sha256(b"HOTFIX-GENESIS-UG59-MVP-AUDIT-ROOT").hexdigest()

KEYS_DIR = Path(os.getenv("HOTFIX_KEYS_DIR", "backend/keys"))
if not KEYS_DIR.is_absolute() and Path.cwd().name == "backend":
    KEYS_DIR = Path.cwd() / "keys"


def _get_or_create_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Retrieves or safely generates an Ed25519 keypair for audit record signing."""
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = KEYS_DIR / "ed25519_audit_private.pem"
    pub_path = KEYS_DIR / "ed25519_audit_public.pem"

    if priv_path.exists() and pub_path.exists():
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(pub_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
        return private_key, public_key

    # Generate new keypair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(priv_path, "wb") as f:
        f.write(priv_bytes)
    with open(pub_path, "wb") as f:
        f.write(pub_bytes)

    return private_key, public_key


def sign_entry_hash(entry_hash: str) -> str:
    """Signs an entry hash with the Ed25519 private key and returns base64 encoded signature."""
    private_key, _ = _get_or_create_keypair()
    sig = private_key.sign(entry_hash.encode("utf-8"))
    return base64.b64encode(sig).decode("utf-8")


def verify_entry_signature(entry_hash: str, signature_b64: str) -> bool:
    """Verifies that an entry hash signature is valid using the Ed25519 public key."""
    _, public_key = _get_or_create_keypair()
    try:
        sig_bytes = base64.b64decode(signature_b64)
        public_key.verify(sig_bytes, entry_hash.encode("utf-8"))
        return True
    except Exception:
        return False


def calculate_entry_hash(
    prev_hash: str,
    actor: str,
    dataset_scope: str,
    query_fingerprint: str,
    expenditure_micro: int,
    cumulative_micro: int,
    mechanism: str,
    receipt_id: str,
    created_at: str
) -> str:
    """Calculates deterministic SHA-256 hash for an audit log entry."""
    payload = f"{prev_hash}|{actor}|{dataset_scope}|{query_fingerprint}|{expenditure_micro}|{cumulative_micro}|{mechanism}|{receipt_id}|{created_at}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_audit_entry(
    conn,
    event_id: str,
    actor: str,
    dataset_scope: str,
    query_fingerprint: str,
    expenditure_micro: int,
    cumulative_micro: int,
    mechanism: str,
    receipt_id: str,
    created_at: str
) -> tuple[str, str]:
    """Appends an entry to the hash-chained audit log within an existing transaction."""
    # Fetch previous entry hash
    last_row = conn.execute(
        "SELECT entry_hash FROM audit_log ORDER BY entry_id DESC LIMIT 1"
    ).fetchone()
    prev_hash = last_row["entry_hash"] if last_row else GENESIS_HASH

    entry_hash = calculate_entry_hash(
        prev_hash,
        actor,
        dataset_scope,
        query_fingerprint,
        expenditure_micro,
        cumulative_micro,
        mechanism,
        receipt_id,
        created_at
    )
    signature = sign_entry_hash(entry_hash)

    conn.execute("""
    INSERT INTO audit_log (
        event_id, actor, dataset_scope, query_fingerprint,
        privacy_expenditure_micro, cumulative_expenditure_micro,
        mechanism, receipt_id, prev_hash, entry_hash, signature, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        event_id, actor, dataset_scope, query_fingerprint,
        expenditure_micro, cumulative_micro,
        mechanism, receipt_id, prev_hash, entry_hash, signature, created_at
    ))

    return entry_hash, signature


def verify_audit_ledger(conn) -> Dict[str, Any]:
    """
    Verifies the cryptographic integrity of the entire audit log.
    Validates:
    1. Previous-hash linkage.
    2. Recalculated entry SHA-256 hash.
    3. Ed25519 digital signature.
    4. Monotonic accounting consistency per dataset scope.
    """
    rows = conn.execute("SELECT * FROM audit_log ORDER BY entry_id ASC").fetchall()
    if not rows:
        return {
            "valid": True,
            "total_entries": 0,
            "verified_entries": 0,
            "tamper_detected": False,
            "error_message": None,
            "details": []
        }

    expected_prev_hash = GENESIS_HASH
    cumulative_tracker: Dict[str, int] = {}
    verified_count = 0

    for r in rows:
        entry_id = r["entry_id"]
        # 1. Verify previous hash link
        if r["prev_hash"] != expected_prev_hash:
            return {
                "valid": False,
                "total_entries": len(rows),
                "verified_entries": verified_count,
                "tamper_detected": True,
                "broken_at_entry": entry_id,
                "error_message": f"Broken hash chain at entry {entry_id}: expected prev_hash {expected_prev_hash}, got {r['prev_hash']}"
            }

        # 2. Recalculate and verify entry hash
        recalc_hash = calculate_entry_hash(
            r["prev_hash"],
            r["actor"],
            r["dataset_scope"],
            r["query_fingerprint"],
            r["privacy_expenditure_micro"],
            r["cumulative_expenditure_micro"],
            r["mechanism"],
            r["receipt_id"],
            r["created_at"]
        )
        if recalc_hash != r["entry_hash"]:
            return {
                "valid": False,
                "total_entries": len(rows),
                "verified_entries": verified_count,
                "tamper_detected": True,
                "broken_at_entry": entry_id,
                "error_message": f"Entry hash mismatch at entry {entry_id}: data modified without updating hash"
            }

        # 3. Verify Ed25519 signature
        if not verify_entry_signature(r["entry_hash"], r["signature"]):
            return {
                "valid": False,
                "total_entries": len(rows),
                "verified_entries": verified_count,
                "tamper_detected": True,
                "broken_at_entry": entry_id,
                "error_message": f"Invalid cryptographic signature at entry {entry_id}"
            }

        # 4. Accounting consistency
        scope = r["dataset_scope"]
        prev_spent = cumulative_tracker.get(scope, 0)
        expected_cum = prev_spent + r["privacy_expenditure_micro"]
        if r["cumulative_expenditure_micro"] != expected_cum:
            return {
                "valid": False,
                "total_entries": len(rows),
                "verified_entries": verified_count,
                "tamper_detected": True,
                "broken_at_entry": entry_id,
                "error_message": f"Accounting inconsistency at entry {entry_id}: expected cumulative {expected_cum}, got {r['cumulative_expenditure_micro']}"
            }

        cumulative_tracker[scope] = expected_cum
        expected_prev_hash = r["entry_hash"]
        verified_count += 1

    return {
        "valid": True,
        "total_entries": len(rows),
        "verified_entries": verified_count,
        "tamper_detected": False,
        "error_message": None
    }


def tamper_audit_entry_for_test(conn, entry_id: int, new_expenditure_micro: int) -> None:
    """Deliberately modifies an audit entry without updating hash/signature (for testing tamper-evidence)."""
    conn.execute(
        "UPDATE audit_log SET privacy_expenditure_micro = ? WHERE entry_id = ?",
        (new_expenditure_micro, entry_id)
    )
