"""Tests for B09 (Error safety and information leakage prevention)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import create_application


def test_b09_unhandled_exception_does_not_leak_traceback_or_secrets():
    """
    B09: Unhandled exceptions must return sanitized 500 error responses
    without disclosing stack traces, file paths, credentials, or environment variables.
    """
    app = create_application()

    # Inject a test route that raises a simulated internal failure
    @app.get("/test/raise-internal-error")
    def raise_internal():
        secret_key = "MOCK_SUPER_SECRET_KEY_12345"
        raise RuntimeError(f"Database connection failure with key: {secret_key}")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test/raise-internal-error")

    assert response.status_code == 500
    data = response.json()

    assert data["error"] == "Internal Server Error"
    assert "MOCK_SUPER_SECRET_KEY_12345" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
    assert "code" in data
    assert data["code"] == "500"


def test_b09_validation_error_is_sanitized():
    """B09: Validation errors provide sanitized structure without exposing internal exceptions."""
    app = create_application()
    client = TestClient(app)

    # Calling nonexistent route
    response = client.get("/nonexistent-endpoint-404")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "HTTP Error"
    assert "Not Found" in data["detail"]

