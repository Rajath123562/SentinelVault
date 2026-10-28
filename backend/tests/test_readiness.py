"""Tests for B03 (Readiness endpoint)."""

from fastapi.testclient import TestClient


def test_b03_readiness_distinguishes_app_from_privacy_readiness(client: TestClient):
    """
    B03: GET /ready accurately reports initialized Phase 1 components
    without implying that unimplemented privacy controls are operational.
    """
    response = client.get("/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["phase"] == "Phase 1"
    assert data["application_initialized"] is True
    assert data["configuration_valid"] is True

    # MUST explicitly distinguish application readiness from privacy readiness
    assert data["privacy_release_ready"] is False
    assert data["privacy_engine_implemented"] is False
    assert data["official_spec_status"] == "NOT_CONFIGURED"
    assert data["evaluation_harness_status"] == "UNAVAILABLE"
    assert "release_disabled_reason" in data
    assert len(data["release_disabled_reason"]) > 0

