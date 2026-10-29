"""Incident response state machine, automated security monitoring, and alert management."""

import json
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.db.connection import get_connection, record_security_event_db

STATE_NORMAL = "NORMAL"
STATE_RESTRICTED = "RESTRICTED"
STATE_RELEASES_DISABLED = "RELEASES_DISABLED"

VALID_INCIDENT_STATES = {STATE_NORMAL, STATE_RESTRICTED, STATE_RELEASES_DISABLED}

PERMITTED_TRANSITIONS = {
    (STATE_NORMAL, STATE_RESTRICTED),
    (STATE_NORMAL, STATE_RELEASES_DISABLED),
    (STATE_RESTRICTED, STATE_RELEASES_DISABLED),
    (STATE_RESTRICTED, STATE_NORMAL),
    (STATE_RELEASES_DISABLED, STATE_RESTRICTED),
    (STATE_RELEASES_DISABLED, STATE_NORMAL),
}

ALERT_STATUS_OPEN = "OPEN"
ALERT_STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
ALERT_STATUS_RESOLVED = "RESOLVED"
ALERT_STATUS_FALSE_POSITIVE = "FALSE_POSITIVE"

VALID_ALERT_STATUSES = {
    ALERT_STATUS_OPEN,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED,
    ALERT_STATUS_FALSE_POSITIVE
}


class IncidentStateError(ValueError):
    """Raised when an invalid state transition or unauthorized operation is requested."""
    pass


class ReleaseBlockedByIncidentError(RuntimeError):
    """Raised when a query release is blocked by active incident state."""
    pass


def get_incident_status(conn=None) -> Dict[str, Any]:
    """Retrieves authoritative incident status and active release constraints."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        row = conn.execute(
            "SELECT current_state, trigger_source, reason, updated_by, updated_at FROM incident_state WHERE id = 1"
        ).fetchone()

        if not row:
            now_iso = datetime.now(timezone.utc).isoformat()
            return {
                "current_state": STATE_NORMAL,
                "trigger_source": "SYSTEM_DEFAULT",
                "reason": "Standard zero-trust gateway operations active.",
                "updated_by": "system",
                "updated_at": now_iso,
                "releases_allowed": True,
                "max_permitted_epsilon": 1.0,
                "status_badge": "OPERATIONAL"
            }

        state = row["current_state"]
        releases_allowed = (state != STATE_RELEASES_DISABLED)
        max_eps = 0.50 if state == STATE_RESTRICTED else (1.0 if state == STATE_NORMAL else 0.0)

        badge_map = {
            STATE_NORMAL: "OPERATIONAL",
            STATE_RESTRICTED: "RESTRICTED_MODE",
            STATE_RELEASES_DISABLED: "FAIL_CLOSED_SUSPENDED"
        }

        return {
            "current_state": state,
            "trigger_source": row["trigger_source"],
            "reason": row["reason"],
            "updated_by": row["updated_by"],
            "updated_at": row["updated_at"],
            "releases_allowed": releases_allowed,
            "max_permitted_epsilon": max_eps,
            "status_badge": badge_map.get(state, "UNKNOWN")
        }
    finally:
        if close_conn:
            conn.close()


def transition_incident_state(
    new_state: str,
    actor: str,
    reason: str,
    trigger_source: str = "ADMIN_MANUAL",
    conn=None
) -> Dict[str, Any]:
    """
    Executes an authorized state transition in the incident response state machine.
    Enforces valid transition paths, mandatory audit justification, and records incident history.
    """
    norm_new = new_state.strip().upper()
    if norm_new not in VALID_INCIDENT_STATES:
        raise IncidentStateError(f"Invalid incident state '{new_state}'. Allowed: {sorted(list(VALID_INCIDENT_STATES))}")

    if not reason or len(reason.strip()) < 10:
        raise IncidentStateError("State transition requires a mandatory, descriptive reason (minimum 10 characters).")

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        current_status = get_incident_status(conn=conn)
        current_state = current_status["current_state"]

        if current_state == norm_new:
            return current_status  # Idempotent no-op

        transition_pair = (current_state, norm_new)
        if transition_pair not in PERMITTED_TRANSITIONS:
            raise IncidentStateError(
                f"Prohibited state transition: '{current_state}' cannot directly transition to '{norm_new}'. "
                f"Valid transition sequence must be followed."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        log_id = f"INCLOG-{secrets.token_hex(8)}"

        with conn:
            conn.execute("""
            UPDATE incident_state 
            SET current_state = ?, trigger_source = ?, reason = ?, updated_by = ?, updated_at = ?
            WHERE id = 1;
            """, (norm_new, trigger_source, reason.strip(), actor, now_iso))

            conn.execute("""
            INSERT INTO incident_log (log_id, prev_state, new_state, actor, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (log_id, current_state, norm_new, actor, reason.strip(), now_iso))

            record_security_event_db(
                conn=conn,
                event_type="INCIDENT_STATE_TRANSITION",
                outcome="SUCCESS",
                actor=actor,
                source_ip="internal",
                resource="gateway.incident_controller",
                action="STATE_TRANSITION",
                details=f"State changed from {current_state} to {norm_new}. Reason: {reason.strip()}"
            )

        return get_incident_status(conn=conn)
    finally:
        if close_conn:
            conn.close()


def trigger_automated_fail_closed(
    trigger_reason: str,
    source: str = "AUTOMATED_SAFETY_CHECK",
    conn=None
) -> None:
    """
    Automatically triggers fail-closed suspension (RELEASES_DISABLED) when critical
    cryptographic or privacy invariants fail.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.execute("""
            UPDATE incident_state 
            SET current_state = ?, trigger_source = ?, reason = ?, updated_by = ?, updated_at = ?
            WHERE id = 1;
            """, (STATE_RELEASES_DISABLED, source, trigger_reason, "system_automated_guard", now_iso))

            conn.execute("""
            INSERT INTO incident_log (log_id, prev_state, new_state, actor, reason, timestamp)
            VALUES (?, 'OPERATIONAL_PREV', ?, 'system_automated_guard', ?, ?);
            """, (f"INCLOG-{secrets.token_hex(8)}", STATE_RELEASES_DISABLED, trigger_reason, now_iso))

            record_security_event_db(
                conn=conn,
                event_type="FAIL_CLOSED_TRIGGERED",
                outcome="RELEASES_DISABLED",
                actor="system_automated_guard",
                source_ip="internal",
                resource="gateway.release_pipeline",
                action="FAIL_CLOSED",
                details=f"Releases disabled fail-closed: {trigger_reason}"
            )

            # Also create High severity alert
            create_security_alert(
                rule_id="RULE_FAIL_CLOSED_CRITICAL",
                title="Critical Privacy Fail-Closed Gate Triggered",
                severity="HIGH",
                actor="system",
                resource="privacy_release_pipeline",
                details=trigger_reason,
                evidence={"trigger_source": source, "action": "RELEASES_DISABLED"},
                conn=conn
            )
    finally:
        if close_conn:
            conn.close()


def create_security_alert(
    rule_id: str,
    title: str,
    severity: str,
    actor: Optional[str] = None,
    resource: Optional[str] = None,
    details: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    conn=None
) -> str:
    """Inserts a persistent security monitoring alert."""
    alert_id = f"ALT-{secrets.token_hex(8)}"
    now_iso = datetime.now(timezone.utc).isoformat()
    evidence_str = json.dumps(evidence or {})

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        conn.execute("""
        INSERT INTO security_alerts (
            alert_id, rule_id, title, severity, status, actor, resource,
            details, evidence_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?);
        """, (
            alert_id, rule_id, title, severity.upper(),
            actor or "unknown", resource or "gateway",
            details or "", evidence_str, now_iso, now_iso
        ))
        conn.commit()
        return alert_id
    finally:
        if close_conn:
            conn.close()


def list_security_alerts(
    conn=None,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    rule_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists security alerts with optional status/severity filtering."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        query = "SELECT * FROM security_alerts WHERE 1=1"
        params: List[Any] = []

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter.upper())
        if severity_filter:
            query += " AND severity = ?"
            params.append(severity_filter.upper())
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(min(max(limit, 1), 200))

        rows = conn.execute(query, params).fetchall()
        alerts = []
        for r in rows:
            d = dict(r)
            try:
                d["evidence"] = json.loads(d.get("evidence_json") or "{}")
            except Exception:
                d["evidence"] = {}
            alerts.append(d)
        return alerts
    finally:
        if close_conn:
            conn.close()


def get_security_alert_detail(alert_id: str, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieves full detail and evidence for a single alert."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        row = conn.execute("SELECT * FROM security_alerts WHERE alert_id = ?", (alert_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["evidence"] = json.loads(d.get("evidence_json") or "{}")
        except Exception:
            d["evidence"] = {}
        return d
    finally:
        if close_conn:
            conn.close()


def acknowledge_security_alert(alert_id: str, actor: str, conn=None) -> Dict[str, Any]:
    """Acknowledges an open security alert."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with conn:
            cursor = conn.execute("""
            UPDATE security_alerts 
            SET status = 'ACKNOWLEDGED', acknowledged_by = ?, acknowledged_at = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'OPEN';
            """, (actor, now_iso, now_iso, alert_id))

            if cursor.rowcount == 0:
                existing = conn.execute("SELECT status FROM security_alerts WHERE alert_id = ?", (alert_id,)).fetchone()
                if not existing:
                    raise KeyError(f"Security alert '{alert_id}' not found.")
                # Already acknowledged or resolved
                return get_security_alert_detail(alert_id, conn=conn)

            record_security_event_db(
                conn=conn,
                event_type="ALERT_ACKNOWLEDGED",
                outcome="SUCCESS",
                actor=actor,
                source_ip="internal",
                resource=alert_id,
                action="ACKNOWLEDGE",
                details=f"Alert {alert_id} acknowledged by {actor}"
            )

        return get_security_alert_detail(alert_id, conn=conn)
    finally:
        if close_conn:
            conn.close()


def resolve_security_alert(
    alert_id: str,
    actor: str,
    resolution_notes: str,
    status: str = "RESOLVED",
    conn=None
) -> Dict[str, Any]:
    """Resolves a security alert with mandatory resolution notes."""
    norm_status = status.strip().upper()
    if norm_status not in {ALERT_STATUS_RESOLVED, ALERT_STATUS_FALSE_POSITIVE}:
        raise ValueError(f"Resolution status must be either 'RESOLVED' or 'FALSE_POSITIVE', got '{status}'")

    if not resolution_notes or len(resolution_notes.strip()) < 5:
        raise ValueError("Resolving an alert requires mandatory resolution notes (minimum 5 characters).")

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with conn:
            cursor = conn.execute("""
            UPDATE security_alerts 
            SET status = ?, resolved_by = ?, resolved_at = ?, resolution_notes = ?, updated_at = ?
            WHERE alert_id = ?;
            """, (norm_status, actor, now_iso, resolution_notes.strip(), now_iso, alert_id))

            if cursor.rowcount == 0:
                raise KeyError(f"Security alert '{alert_id}' not found.")

            record_security_event_db(
                conn=conn,
                event_type="ALERT_RESOLVED",
                outcome="SUCCESS",
                actor=actor,
                source_ip="internal",
                resource=alert_id,
                action="RESOLVE",
                details=f"Alert {alert_id} marked as {norm_status} by {actor}. Notes: {resolution_notes.strip()}"
            )

        return get_security_alert_detail(alert_id, conn=conn)
    finally:
        if close_conn:
            conn.close()


def evaluate_detection_rules(
    event_type: str,
    actor: str,
    outcome: str,
    details: str,
    resource: str = "gateway",
    conn=None
) -> None:
    """
    Evaluates centralized threat detection rules based on incoming security events.
    Triggers automated alerts when thresholds are reached.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        # Rule 1: Account Lockout
        if event_type in ("ACCOUNT_LOCKOUT", "ACCOUNT_LOCKED") or "LOCKOUT" in outcome.upper() or "LOCKED" in event_type.upper():
            create_security_alert(
                rule_id="RULE_ACCOUNT_LOCKOUT",
                title=f"Account Temporarily Locked: {actor}",
                severity="HIGH",
                actor=actor,
                resource=resource,
                details=f"5 consecutive authentication failures triggered a 15-minute lockout for user '{actor}'.",
                evidence={"event_type": event_type, "outcome": outcome, "details": details},
                conn=conn
            )

        # Rule 2: Multiple Authentication Failures (Brute-Force Detection Threshold = 3)
        elif event_type in ("LOGIN", "LOGIN_FAILED") and outcome in ("FAILURE", "DENIED"):
            count_row = conn.execute(
                "SELECT COUNT(*) as c FROM security_events WHERE event_type IN ('LOGIN', 'LOGIN_FAILED') AND outcome IN ('FAILURE', 'DENIED') AND actor = ? AND timestamp > datetime('now', '-15 minutes')",
                (actor,)
            ).fetchone()
            recent_fails = count_row["c"] if count_row else 1
            if recent_fails >= 3:
                create_security_alert(
                    rule_id="RULE_BRUTE_FORCE_BURST",
                    title=f"Repeated Authentication Failures: {actor}",
                    severity="MEDIUM",
                    actor=actor,
                    resource="auth_service",
                    details=f"{recent_fails} failed login attempts recorded for '{actor}' within 15 minutes.",
                    evidence={"failed_count": recent_fails},
                    conn=conn
                )

        # Rule 3: Unauthorized Resource Access
        elif outcome in ("DENIED", "FORBIDDEN") or event_type in ("UNAUTHORIZED_ACCESS", "AUTHORIZATION_DENIAL"):
            create_security_alert(
                rule_id="RULE_UNAUTHORIZED_ACCESS",
                title=f"Unauthorized Access Attempt by {actor}",
                severity="MEDIUM",
                actor=actor,
                resource=resource,
                details=details or "User attempted action exceeding their assigned role permissions.",
                evidence={"event_type": event_type, "outcome": outcome},
                conn=conn
            )

        # Rule 4: Cryptographic Integrity Tampering
        elif "TAMPER" in event_type.upper() or "TAMPER" in outcome.upper():
            create_security_alert(
                rule_id="RULE_INTEGRITY_TAMPER",
                title="Cryptographic Ledger Tampering Detected",
                severity="HIGH",
                actor=actor,
                resource=resource,
                details=details or "Cryptographic signature or hash chain link validation failed.",
                evidence={"event_type": event_type, "outcome": outcome, "details": details},
                conn=conn
            )
            # Automatic fail-closed trigger on cryptographic tampering
            trigger_automated_fail_closed(
                trigger_reason=f"Automated fail-closed safety trigger: Cryptographic tampering detected ({details})",
                source="RULE_INTEGRITY_TAMPER",
                conn=conn
            )

        # Rule 5: Budget Exhaustion Repeated Attempt
        elif event_type == "BUDGET_EXHAUSTION_ATTEMPT":
            create_security_alert(
                rule_id="RULE_BUDGET_EXHAUSTION",
                title=f"Privacy Budget Exhaustion Query Attempt: {actor}",
                severity="LOW",
                actor=actor,
                resource=resource,
                details=details or "User submitted query when available privacy budget was insufficient.",
                evidence={"event_type": event_type, "outcome": outcome},
                conn=conn
            )
    finally:
        if close_conn:
            conn.close()

