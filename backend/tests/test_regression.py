"""Tests for B12 (Regression and release guard verification)."""

from fastapi.testclient import TestClient


def test_b12_fail_closed_release_guard_route(client: TestClient):
    """
    B12: Verifies that any query release endpoint rejects calls with HTTP 403 Forbidden
    in Phase 1 to prevent unauthorized data exposure.
    """
    response_get = client.get("/api/v1/query/release")
    assert response_get.status_code == 403
    data_get = response_get.json()
    assert data_get["code"] == "PRIVACY_RELEASE_DISABLED"

    response_post = client.post("/api/v1/query/release", json={"query": "SELECT count(*) FROM health"})
    assert response_post.status_code == 403
    data_post = response_post.json()
    assert data_post["code"] == "PRIVACY_RELEASE_DISABLED"


def test_b12_fixture_isolation():
    """B12: Ensure test fixture is cleanly isolated and marked as non-official test stub."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parent / "fixtures" / "sample_dataset_stub.json"
    assert fixture_path.exists(), "Sample test fixture should exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["is_official_dataset"] is False
    assert "mock_id" in data["records"][0]

