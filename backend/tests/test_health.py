"""Tests for B01 (Application startup) and B02 (Health endpoint)."""

from fastapi.testclient import TestClient


def test_b01_application_startup():
    """B01: Verify that the FastAPI application initializes cleanly without raising exceptions."""
    from app.main import create_application
    app = create_application()
    assert app is not None
    assert app.title == "HOTFIX Privacy-by-Design Analytics Gateway"
    assert app.version == "0.1.0"


def test_b02_health_endpoint(client: TestClient):
    """B02: GET /health returns HTTP 200, valid JSON, and does not claim privacy engine is operational."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "hotfix-backend"
    assert "timestamp" in data
    # Ensure no secrets or operational privacy claims are present
    assert "password" not in response.text.lower()
    assert "secret" not in response.text.lower()
    assert "differential_privacy_ready" not in data
