"""Tests for B04 (System status), B10 (No false feature claims), and B11 (API contract consistency)."""

from fastapi.testclient import TestClient


def test_b04_system_status_schema(client: TestClient):
    """B04: GET /api/system/status returns a response strictly adhering to its documented schema."""
    response = client.get("/api/system/status")
    assert response.status_code == 200

    data = response.json()
    assert data["project_name"] == "HOTFIX Privacy-by-Design Analytics Gateway"
    assert data["project_code"] == "HOTFIX"
    assert data["team_id"] == "UG 59"
    assert data["current_phase"] == "Phase 1"
    assert data["application_health"] == "HEALTHY"
    assert data["configuration_valid"] is True
    assert data["privacy_releases_enabled"] is False
    assert "release_disabled_reason" in data
    assert data["official_spec_status"] == "NOT_CONFIGURED"
    assert data["official_harness_status"] == "NOT_INTEGRATED"
    assert "server_time" in data
    assert isinstance(data["capabilities"], list)
    assert len(data["capabilities"]) >= 10


def test_b10_no_false_feature_claims(client: TestClient):
    """
    B10: The status API must NOT report unimplemented authentication,
    accounting, risk evaluation, or audit verification as operational.
    """
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()

    capabilities_by_id = {cap["id"]: cap for cap in data["capabilities"]}

    # Verify unimplemented modules are honestly designated as PLANNED
    assert capabilities_by_id["CAP-03-AUTH-RBAC"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-04-DATASET-VALIDATION"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-05-QUERY-INTERFACE"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-06-DP-ENGINE"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-07-BUDGET-LEDGER"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-08-RISK-EVALUATION"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-09-UTILITY-BENCHMARK"]["status"] == "PLANNED"
    assert capabilities_by_id["CAP-10-AUDIT-RECEIPTS"]["status"] == "PLANNED"

    # Verify only genuine Phase 1 foundation capabilities are marked IMPLEMENTED
    assert capabilities_by_id["CAP-01-FOUNDATION"]["status"] == "IMPLEMENTED"
    assert capabilities_by_id["CAP-02-CONFIG-GATES"]["status"] == "IMPLEMENTED"


def test_b11_api_contract_consistency(client: TestClient):
    """B11: Test response headers, content types, status codes, and JSON structure."""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    # Contract checks on capability objects
    data = response.json()
    for cap in data["capabilities"]:
        assert "id" in cap and isinstance(cap["id"], str)
        assert "name" in cap and isinstance(cap["name"], str)
        assert "status" in cap and cap["status"] in {"IMPLEMENTED", "PLANNED", "BLOCKED", "NOT_CONFIGURED"}
        assert "phase" in cap and isinstance(cap["phase"], str)
        assert "description" in cap and isinstance(cap["description"], str)
