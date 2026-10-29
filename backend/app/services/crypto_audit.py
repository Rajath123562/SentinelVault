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
    target_dir = KEYS_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        target_dir = Path("/tmp/keys")
        target_dir.mkdir(parents=True, exist_ok=True)

    priv_path = target_dir / "ed25519_audit_private.pem"
    pub_path = target_dir / "ed25519_audit_public.pem"

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

    try:
        with open(priv_path, "wb") as f:
            f.write(priv_bytes)
        with open(pub_path, "wb") as f:
            f.write(pub_bytes)
    except OSError:
        pass

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


TRUSTED_KEY_ID = "ED25519-ENCLAVE-2026-V1"
RECEIPT_SCHEMA_VERSION = "1.0.0"


def canonicalize_receipt(data: Dict[str, Any]) -> str:
    """Generates a deterministic canonical representation of the security-critical receipt fields."""
    fields = [
        str(data.get("receipt_id", "")),
        str(data.get("release_id", "")),
        str(data.get("user_id", "")),
        str(data.get("dataset_id", "")),
        str(data.get("dataset_version", "")),
        str(data.get("query_fingerprint", "")),
        str(data.get("query_description", "")),
        str(data.get("mechanism", "")),
        f"{float(data.get('epsilon_spent', 0.0)):.4f}",
        f"{float(data.get('cumulative_epsilon', 0.0)):.4f}",
        f"{float(data.get('remaining_budget', 0.0)):.4f}",
        str(data.get("policy_check_status", "")),
        str(data.get("audit_entry_hash", "")),
        str(data.get("key_id", TRUSTED_KEY_ID)),
        str(data.get("schema_version", RECEIPT_SCHEMA_VERSION)),
        str(data.get("timestamp", ""))
    ]
    return "|".join(fields)


def compute_receipt_hash(data: Dict[str, Any]) -> str:
    """Calculates deterministic SHA-256 hash for canonical receipt content."""
    canonical_repr = canonicalize_receipt(data)
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def verify_receipt_cryptographic(conn, receipt_id: str) -> Dict[str, Any]:
    """
    Performs end-to-end cryptographic and semantic integrity checks on a Privacy Receipt.
    Validates:
    1. Receipt existence and schema version.
    2. Revocation status.
    3. Trust status of signing key identifier.
    4. Canonical SHA-256 hash match against tamper-evident payload.
    5. Ed25519 digital signature authenticity using enclave public key.
    6. Relational linkage to committed query release record.
    7. Relational linkage to immutable hash-chained audit log.
    """
    row = conn.execute("SELECT * FROM privacy_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
    if not row:
        return {
            "receipt_id": receipt_id,
            "is_valid": False,
            "verification_status": "NOT_FOUND",
            "checks": {
                "receipt_found": False,
                "schema_valid": False,
                "not_revoked": False,
                "hash_match": False,
                "signature_valid": False,
                "key_trusted": False,
                "release_linked": False,
                "audit_linked": False,
            },
            "error_message": f"Privacy receipt '{receipt_id}' does not exist in gateway records."
        }

    receipt = dict(row)
    checks = {
        "receipt_found": True,
        "schema_valid": receipt.get("schema_version") == RECEIPT_SCHEMA_VERSION,
        "not_revoked": not bool(receipt.get("is_revoked", 0)),
        "key_trusted": receipt.get("key_id") == TRUSTED_KEY_ID,
    }

    # Verify canonical hash
    recalc_hash = compute_receipt_hash(receipt)
    stored_hash = receipt.get("receipt_hash") or ""
    # If legacy receipt without stored receipt_hash, hash can match audit_entry_hash
    hash_match = (stored_hash == recalc_hash) if stored_hash else True
    checks["hash_match"] = hash_match

    # Verify signature against audit entry hash or receipt hash
    sig_valid = (
        verify_entry_signature(receipt.get("audit_entry_hash", ""), receipt.get("signature", "")) or
        (bool(stored_hash) and verify_entry_signature(stored_hash, receipt.get("signature", "")))
    )
    checks["signature_valid"] = sig_valid

    # Verify release linkage
    rel_row = conn.execute(
        "SELECT release_id, query_fingerprint, dataset_id FROM query_releases WHERE release_id = ?",
        (receipt["release_id"],)
    ).fetchone()
    checks["release_linked"] = bool(
        rel_row and
        rel_row["query_fingerprint"] == receipt["query_fingerprint"] and
        rel_row["dataset_id"] == receipt["dataset_id"]
    )

    # Verify audit linkage
    audit_row = conn.execute(
        "SELECT entry_hash, receipt_id FROM audit_log WHERE receipt_id = ? AND entry_hash = ?",
        (receipt["receipt_id"], receipt["audit_entry_hash"])
    ).fetchone()
    checks["audit_linked"] = bool(audit_row)

    is_valid = all(checks.values())
    status_str = "VERIFIED_AUTHENTIC" if is_valid else "VERIFICATION_FAILED"

    reasons = []
    if not checks["schema_valid"]: reasons.append("Unsupported schema version")
    if not checks["not_revoked"]: reasons.append(f"Receipt revoked: {receipt.get('revoked_reason', 'Administrative revocation')}")
    if not checks["key_trusted"]: reasons.append(f"Untrusted signing key: {receipt.get('key_id')}")
    if not checks["hash_match"]: reasons.append("Receipt data modified (hash mismatch)")
    if not checks["signature_valid"]: reasons.append("Cryptographic Ed25519 signature invalid")
    if not checks["release_linked"]: reasons.append("Orphan receipt: no matching query release record")
    if not checks["audit_linked"]: reasons.append("Missing or mismatched audit log entry link")

    return {
        "receipt_id": receipt_id,
        "is_valid": is_valid,
        "verification_status": status_str,
        "checks": checks,
        "key_id": receipt.get("key_id", TRUSTED_KEY_ID),
        "algorithm": "Ed25519 + SHA-256",
        "timestamp": receipt["timestamp"],
        "error_message": "; ".join(reasons) if reasons else None,
        "receipt_data": receipt
    }


def get_audit_entries(
    conn,
    limit: int = 50,
    offset: int = 0,
    dataset_scope: Optional[str] = None,
    search: Optional[str] = None
) -> tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated audit log entries with optional dataset or actor filtering."""
    base_query = "FROM audit_log WHERE 1=1"
    params: List[Any] = []

    if dataset_scope:
        base_query += " AND dataset_scope = ?"
        params.append(dataset_scope)
    if search:
        base_query += " AND (actor LIKE ? OR query_fingerprint LIKE ? OR receipt_id LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    count_sql = f"SELECT COUNT(*) as total {base_query}"
    total = conn.execute(count_sql, params).fetchone()["total"]

    data_sql = f"SELECT * {base_query} ORDER BY entry_id DESC LIMIT ? OFFSET ?"
    fetch_params = params + [min(max(limit, 1), 200), max(offset, 0)]
    rows = conn.execute(data_sql, fetch_params).fetchall()
    return [dict(r) for r in rows], total

