"""Pytest fixtures for HOTFIX backend tests."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import create_application
from app.core.config import get_settings
from app.db.connection import get_connection, init_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes the database schema once per session."""
    init_database()


@pytest.fixture(scope="session")
def client():
    """Provides a TestClient connected to the FastAPI application."""
    app = create_application()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def app_settings():
    """Provides validated application settings."""
    return get_settings()


@pytest.fixture(autouse=True)
def reset_budgets_and_users():
    """Resets dataset budgets, user lockout counters, query releases, receipts, and audit log between test cases."""
    conn = get_connection()
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.execute("""
            UPDATE budget_ledger 
            SET spent_micro_epsilon = 0, remaining_micro_epsilon = cap_micro_epsilon, updated_at = ?;
            """, (now_iso,))
            conn.execute("""
            UPDATE users SET failed_attempts = 0, locked_until = NULL;
            """)
            conn.execute("DELETE FROM audit_log;")
            conn.execute("DELETE FROM privacy_receipts;")
            conn.execute("DELETE FROM query_releases;")
    finally:
        conn.close()
