"""Authentication service managing passwords, temporary lockouts, sessions, MFA, and security events."""

import hmac
import struct
import time
import base64
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List
from app.db.connection import get_connection, verify_password, verify_dummy_password, record_security_event_db

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15
SESSION_DURATION_HOURS = 8
IP_RATE_LIMIT_MAX = 30
IP_RATE_LIMIT_WINDOW_SEC = 60

# Role-Based Access Control: Granular Permission Registry
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "analyst": {
        "system.status.read",
        "dataset.metadata.read",
        "dataset.query.execute",
        "receipt.read.own",
        "audit.verify",
    },
    "data_steward": {
        "system.status.read",
        "dataset.metadata.read",
        "receipt.read.authorized",
        "audit.verify",
        "security.events.read",
        "security.policy.manage",
        "dataset.manage",
        "session.revoke",
    },
    "auditor": {
        "system.status.read",
        "dataset.metadata.read",
        "receipt.read.authorized",
        "audit.verify",
        "security.events.read",
        "evaluation.status.read",
    },
    "admin": {
        "system.status.read",
        "dataset.metadata.read",
        "dataset.query.execute",
        "receipt.read.authorized",
        "audit.verify",
        "security.events.read",
        "security.policy.manage",
        "user.manage",
        "session.revoke",
    }
}


class AuthenticationError(ValueError):
    """Raised on invalid credentials or expired sessions."""
    pass


class AccountLockedError(AuthenticationError):
    """Raised when an account is temporarily locked."""
    pass


class RateLimitExceededError(AuthenticationError):
    """Raised when IP or request rate limits are exceeded."""
    pass


def has_permission(role: str, permission: str) -> bool:
    """Verifies whether a given role holds the requested permission identifier."""
    return permission in ROLE_PERMISSIONS.get(role.lower(), set())


# -------------------------------------------------------------
# NETWORK & IP RATE LIMITING
# -------------------------------------------------------------

def check_ip_rate_limit(conn, client_ip: str, max_requests: int = IP_RATE_LIMIT_MAX, window_sec: int = IP_RATE_LIMIT_WINDOW_SEC) -> None:
    """Checks and increments IP-based sliding window rate limit transactionally."""
    if not client_ip or client_ip in ("127.0.0.1", "testserver", "localhost", "testclient"):
        # For testing and local loopback, allow high volume
        max_requests = 10000

    now_ts = int(time.time())
    key = f"ip:{client_ip}"
    
    row = conn.execute("SELECT window_start, request_count FROM rate_limits WHERE key = ?", (key,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO rate_limits (key, window_start, request_count, updated_at) VALUES (?, ?, 1, ?)",
            (key, now_ts, datetime.now(timezone.utc).isoformat())
        )
        return

    window_start = row["window_start"]
    count = row["request_count"]

    if now_ts - window_start > window_sec:
        # Window expired, reset
        conn.execute(
            "UPDATE rate_limits SET window_start = ?, request_count = 1, updated_at = ? WHERE key = ?",
            (now_ts, datetime.now(timezone.utc).isoformat(), key)
        )
    else:
        if count >= max_requests:
            record_security_event_db(
                conn,
                event_type="RATE_LIMITED",
                outcome="DENIED",
                source_ip=client_ip,
                details=f"IP exceeded {max_requests} requests per {window_sec}s window"
            )
            raise RateLimitExceededError(f"Network rate limit exceeded. Maximum {max_requests} requests allowed per {window_sec}s.")
        
        conn.execute(
            "UPDATE rate_limits SET request_count = request_count + 1, updated_at = ? WHERE key = ?",
            (datetime.now(timezone.utc).isoformat(), key)
        )


# -------------------------------------------------------------
# RFC 6238 TOTP MULTI-FACTOR AUTHENTICATION
# -------------------------------------------------------------

def generate_totp_secret() -> str:
    """Generates a cryptographically secure 20-byte Base32 secret for TOTP enrolment."""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode("ascii").replace("=", "")


def compute_totp_code(secret_b32: str, time_step: int) -> str:
    """Computes a 6-digit TOTP code for a specific time step using HMAC-SHA1."""
    key = base64.b32decode(secret_b32.upper(), casefold=True)
    msg = struct.pack(">Q", time_step)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1000000:06d}"


def generate_totp_code(secret_b32: str) -> str:
    """Generates the current valid 6-digit TOTP code for the given secret."""
    return compute_totp_code(secret_b32, int(time.time() // 30))


def verify_totp_code(secret_b32: str, code: str, window: int = 1) -> bool:
    """
    Verifies a 6-digit TOTP code against a secret with window tolerance (+/- 30s).
    Uses constant-time comparison to prevent timing analysis.
    """
    if not code or len(code.strip()) != 6:
        return False

    current_t = int(time.time() // 30)
    for offset in range(-window, window + 1):
        expected = compute_totp_code(secret_b32, current_t + offset)
        if secrets.compare_digest(code.strip(), expected):
            return True
    return False


def enroll_mfa_for_user(username: str) -> Dict[str, Any]:
    """Generates an MFA secret and recovery codes for enrollment."""
    norm_user = username.strip().lower()
    conn = get_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (norm_user,)).fetchone()
        if not user:
            raise AuthenticationError("User not found")

        secret = generate_totp_secret()
        # Generate 5 recovery codes
        raw_recovery = [secrets.token_hex(4).upper() for _ in range(5)]
        recovery_hashes = [hashlib.sha256(c.encode("utf-8")).hexdigest() for c in raw_recovery]
        recovery_str = ",".join(recovery_hashes)

        # Store secret in pending state
        with conn:
            conn.execute(
                "UPDATE users SET mfa_secret = ?, mfa_recovery_codes_hash = ? WHERE username = ?",
                (secret, recovery_str, norm_user)
            )

        uri = f"otpauth://totp/HOTFIX:{norm_user}?secret={secret}&issuer=HOTFIX-Gateway"
        return {
            "secret": secret,
            "otpauth_uri": uri,
            "recovery_codes": raw_recovery,
            "notice": "Store recovery codes safely. Confirm enrollment by verifying your first 6-digit code."
        }
    finally:
        conn.close()


def confirm_mfa_enrollment(username: str, code: str) -> bool:
    """Confirms enrollment by verifying a code generated with the newly stored secret."""
    norm_user = username.strip().lower()
    conn = get_connection()
    try:
        user = conn.execute("SELECT mfa_secret FROM users WHERE username = ?", (norm_user,)).fetchone()
        if not user or not user["mfa_secret"]:
            raise AuthenticationError("No pending MFA enrollment found")

        if not verify_totp_code(user["mfa_secret"], code):
            record_security_event_db(conn, "MFA_FAILED", "FAILURE", actor=norm_user, details="Invalid confirmation code during MFA setup")
            raise AuthenticationError("Invalid verification code. Please check your authenticator clock.")

        with conn:
            conn.execute("UPDATE users SET mfa_enabled = 1 WHERE username = ?", (norm_user,))
            record_security_event_db(conn, "MFA_ENROLLED", "SUCCESS", actor=norm_user, details="MFA successfully activated")
        return True
    finally:
        conn.close()


# -------------------------------------------------------------
# CORE AUTHENTICATION & LOGIN
# -------------------------------------------------------------

def login_user(username: str, password: str, client_ip: str = "unknown", mfa_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Authenticates user credentials with:
    - Constant-time password verification (side-channel safe).
    - Authoritative server-side 5-consecutive-failed-attempt lockout.
    - IP-level rate limiting.
    - Multi-Factor Authentication (MFA) check if enabled.
    - Structured security event logging.
    """
    norm_user = (username or "").strip().lower()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    conn = get_connection()
    try:
        # 1. Network Rate Limit Check
        check_ip_rate_limit(conn, client_ip)

        # 2. Look up user
        user = conn.execute("SELECT * FROM users WHERE username = ?", (norm_user,)).fetchone()
        if not user:
            # Constant-time dummy verification prevents timing disclosure of username existence
            verify_dummy_password(password)
            with conn:
                record_security_event_db(
                    conn, event_type="LOGIN_FAILED", outcome="FAILURE",
                    actor=norm_user, source_ip=client_ip, action="LOGIN", details="Nonexistent user attempt"
                )
            raise AuthenticationError("Invalid username or password")

        # 3. Check Account Status & Lockout
        if user["locked_until"]:
            locked_until_dt = datetime.fromisoformat(user["locked_until"])
            if now < locked_until_dt:
                remaining_sec = int((locked_until_dt - now).total_seconds())
                with conn:
                    record_security_event_db(
                        conn, event_type="ACCOUNT_LOCKED", outcome="DENIED",
                        actor=norm_user, source_ip=client_ip, action="LOGIN",
                        details=f"Attempt rejected during active lockout. Remaining: {remaining_sec}s"
                    )
                raise AccountLockedError(
                    f"Account is temporarily locked due to {LOCKOUT_THRESHOLD} consecutive failed login attempts. "
                    f"Please try again in {remaining_sec} seconds."
                )
            else:
                # Lockout expired, reset counter atomically
                with conn:
                    conn.execute(
                        "UPDATE users SET failed_attempts = 0, locked_until = NULL, status = 'ACTIVE' WHERE username = ?",
                        (norm_user,)
                    )

        # 4. Verify Password Hash
        if not verify_password(password, user["password_hash"], user["salt"]):
            new_failed = user["failed_attempts"] + 1
            locked_until_val = None

            with conn:
                if new_failed >= LOCKOUT_THRESHOLD:
                    locked_until_dt = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                    locked_until_val = locked_until_dt.isoformat()
                    conn.execute("""
                    UPDATE users 
                    SET failed_attempts = ?, locked_until = ?, status = 'LOCKED'
                    WHERE username = ?;
                    """, (new_failed, locked_until_val, norm_user))
                    record_security_event_db(
                        conn, event_type="ACCOUNT_LOCKED", outcome="FAILURE",
                        actor=norm_user, source_ip=client_ip,
                        details=f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes after {new_failed} consecutive failures"
                    )
                else:
                    conn.execute("""
                    UPDATE users 
                    SET failed_attempts = ?
                    WHERE username = ?;
                    """, (new_failed, norm_user))
                    record_security_event_db(
                        conn, event_type="LOGIN_FAILED", outcome="FAILURE",
                        actor=norm_user, source_ip=client_ip, action="LOGIN",
                        details=f"Invalid password (consecutive failure {new_failed}/{LOCKOUT_THRESHOLD})"
                    )

            if locked_until_val:
                raise AccountLockedError(
                    f"Account locked: {LOCKOUT_THRESHOLD} consecutive failed attempts reached. "
                    f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes."
                )
            raise AuthenticationError("Invalid username or password")

        # 5. Check Multi-Factor Authentication if enabled
        if user["mfa_enabled"] == 1:
            if not mfa_code:
                with conn:
                    record_security_event_db(
                        conn, event_type="MFA_REQUIRED", outcome="CHALLENGE",
                        actor=norm_user, source_ip=client_ip, action="LOGIN", details="Second factor required"
                    )
                raise AuthenticationError("MFA verification code required")

            if not verify_totp_code(user["mfa_secret"], mfa_code):
                with conn:
                    record_security_event_db(
                        conn, event_type="MFA_FAILED", outcome="FAILURE",
                        actor=norm_user, source_ip=client_ip, action="LOGIN", details="Incorrect TOTP code"
                    )
                raise AuthenticationError("Invalid MFA verification code")

        # 6. Authentication Successful
        token = secrets.token_hex(32)
        expires_at = (now + timedelta(hours=SESSION_DURATION_HOURS)).isoformat()

        with conn:
            # Reset failure counter and update last login
            conn.execute("""
            UPDATE users 
            SET failed_attempts = 0, locked_until = NULL, status = 'ACTIVE', last_login_at = ?
            WHERE username = ?;
            """, (now_iso, norm_user))

            # Store new session
            conn.execute("""
            INSERT INTO sessions (token, username, role, expires_at, created_at, last_accessed_at, is_revoked, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?);
            """, (token, user["username"], user["role"], expires_at, now_iso, now_iso, client_ip))

            record_security_event_db(
                conn, event_type="LOGIN_SUCCESS", outcome="SUCCESS",
                actor=norm_user, source_ip=client_ip, action="LOGIN", details="Authenticated successfully"
            )

        perms = list(ROLE_PERMISSIONS.get(user["role"].lower(), set()))
        return {
            "token": token,
            "username": user["username"],
            "user_id": user["user_id"] or user["username"],
            "role": user["role"],
            "permissions": perms,
            "expires_at": expires_at,
            "mfa_active": bool(user["mfa_enabled"])
        }
    finally:
        conn.close()


def logout_user(token: str, client_ip: str = "unknown") -> None:
    """Terminates an active session and records the logout security event."""
    conn = get_connection()
    try:
        session = conn.execute("SELECT username FROM sessions WHERE token = ?", (token,)).fetchone()
        actor = session["username"] if session else "unknown"

        with conn:
            conn.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (token,))
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            record_security_event_db(
                conn, event_type="LOGOUT", outcome="SUCCESS",
                actor=actor, source_ip=client_ip, details="Session explicitly terminated by user"
            )
    finally:
        conn.close()


def revoke_session_administrative(admin_actor: str, target_token: str, reason: str = "Administrative revocation") -> bool:
    """Revokes a session by administrative command."""
    conn = get_connection()
    try:
        session = conn.execute("SELECT username FROM sessions WHERE token = ?", (target_token,)).fetchone()
        if not session:
            return False

        with conn:
            conn.execute("UPDATE sessions SET is_revoked = 1 WHERE token = ?", (target_token,))
            conn.execute("DELETE FROM sessions WHERE token = ?", (target_token,))
            record_security_event_db(
                conn, event_type="SESSION_REVOKED", outcome="SUCCESS",
                actor=admin_actor, resource=f"session_for_{session['username']}", details=reason
            )
        return True
    finally:
        conn.close()


def get_session_user(token: str) -> Dict[str, Any]:
    """Validates session token and returns authoritative server-side user details with permissions."""
    if not token:
        raise AuthenticationError("Authorization token required")

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        session = conn.execute(
            """
            SELECT s.*, u.user_id, u.status as user_status, u.mfa_enabled 
            FROM sessions s
            JOIN users u ON s.username = u.username
            WHERE s.token = ? AND s.expires_at > ? AND s.is_revoked = 0;
            """,
            (token, now_iso)
        ).fetchone()

        if not session:
            raise AuthenticationError("Invalid, revoked, or expired session token")

        if session["user_status"] != "ACTIVE":
            raise AuthenticationError(f"User account is {session['user_status']}")

        # Touch last_accessed_at
        with conn:
            conn.execute("UPDATE sessions SET last_accessed_at = ? WHERE token = ?", (now_iso, token))

        role = session["role"].lower()
        perms = list(ROLE_PERMISSIONS.get(role, set()))

        return {
            "username": session["username"],
            "user_id": session["user_id"] or session["username"],
            "role": session["role"],
            "permissions": perms,
            "expires_at": session["expires_at"],
            "mfa_active": bool(session["mfa_enabled"])
        }
    finally:
        conn.close()
