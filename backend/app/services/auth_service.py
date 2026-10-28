"""Authentication service managing passwords, temporary lockouts, and sessions."""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from app.db.connection import get_connection, verify_password

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15
SESSION_DURATION_HOURS = 8


class AuthenticationError(ValueError):
    """Raised on invalid credentials or expired sessions."""
    pass


class AccountLockedError(AuthenticationError):
    """Raised when an account is temporarily locked."""
    pass


def login_user(username: str, password: str) -> Dict[str, Any]:
    """
    Authenticates user credentials.
    Enforces temporary account lockout after 5 consecutive failed attempts.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    conn = get_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            # Generic error preventing username enumeration
            raise AuthenticationError("Invalid username or password")

        # Check existing lockout
        if user["locked_until"]:
            locked_until_dt = datetime.fromisoformat(user["locked_until"])
            if now < locked_until_dt:
                remaining_sec = int((locked_until_dt - now).total_seconds())
                raise AccountLockedError(
                    f"Account is temporarily locked due to {LOCKOUT_THRESHOLD} consecutive failed login attempts. "
                    f"Please try again in {remaining_sec} seconds."
                )
            else:
                # Lockout expired, reset counter
                conn.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
                    (username,)
                )

        # Verify password
        if not verify_password(password, user["password_hash"], user["salt"]):
            new_failed = user["failed_attempts"] + 1
            locked_until_val = None
            if new_failed >= LOCKOUT_THRESHOLD:
                locked_until_dt = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                locked_until_val = locked_until_dt.isoformat()

            conn.execute("""
            UPDATE users 
            SET failed_attempts = ?, locked_until = ?
            WHERE username = ?;
            """, (new_failed, locked_until_val, username))
            conn.commit()

            if locked_until_val:
                raise AccountLockedError(
                    f"Account locked: {LOCKOUT_THRESHOLD} consecutive failed attempts reached. "
                    f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes."
                )
            raise AuthenticationError("Invalid username or password")

        # Success: reset failed attempts and generate session
        token = secrets.token_hex(32)
        expires_at = (now + timedelta(hours=SESSION_DURATION_HOURS)).isoformat()

        conn.execute("""
        UPDATE users 
        SET failed_attempts = 0, locked_until = NULL 
        WHERE username = ?;
        """, (username,))

        conn.execute("""
        INSERT INTO sessions (token, username, role, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?);
        """, (token, user["username"], user["role"], expires_at, now_iso))

        conn.commit()

        return {
            "token": token,
            "username": user["username"],
            "role": user["role"],
            "expires_at": expires_at
        }
    finally:
        conn.close()


def logout_user(token: str) -> None:
    """Terminates an active session."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def get_session_user(token: str) -> Dict[str, Any]:
    """Validates session token and returns current user details."""
    if not token:
        raise AuthenticationError("Authorization token required")

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        session = conn.execute(
            "SELECT * FROM sessions WHERE token = ? AND expires_at > ?",
            (token, now_iso)
        ).fetchone()

        if not session:
            raise AuthenticationError("Invalid or expired session token")

        return {
            "username": session["username"],
            "role": session["role"],
            "expires_at": session["expires_at"]
        }
    finally:
        conn.close()
