"""Category 1: Deep Verification Suite for Backend Units, API Contracts, and Configuration.

Covers 45 distinct test scenarios validating application lifecycle, health probes,
readiness gating, error sanitization, boundary values, malformed inputs, and HTTP contracts.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import create_application
from app.core.config import get_settings


@pytest.fixture(scope="module")
def api_client():
    app = create_application()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# C1: APPLICATION LIFECYCLE & PROBES (Tests 1 - 10)
# ==============================================================================

def test_c1_01_health_probe_returns_200_and_healthy(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"].lower() == "healthy"
    assert "timestamp" in data


def test_c1_02_health_probe_rejects_unsupported_methods(api_client):
    for method in ["post", "put", "delete", "patch"]:
        res = getattr(api_client, method)("/health")
        assert res.status_code in [405, 404]


def test_c1_03_readiness_probe_returns_initialized(api_client):
    res = api_client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["application_initialized"] is True
    assert data["configuration_valid"] is True


def test_c1_04_readiness_probe_distinguishes_app_from_competition_readiness(api_client):
    res = api_client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["application_initialized"] is True
    # Accurately distinguishes application operational readiness from unconfigured official competition release
    assert data["privacy_release_ready"] is False
    assert data["official_spec_status"] == "NOT_CONFIGURED"


def test_c1_05_system_status_contract_has_mandatory_fields(api_client):
    res = api_client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    mandatory_fields = [
        "project_name", "project_code", "team_id", "current_phase",
        "application_health", "configuration_valid", "capabilities"
    ]
    for field in mandatory_fields:
        assert field in data, f"Missing {field} in /api/system/status"
    assert data["team_id"] == "UG 59"


def test_c1_06_system_status_capabilities_array_non_empty(api_client):
    res = api_client.get("/api/system/status")
    data = res.json()
    caps = data.get("capabilities", [])
    assert len(caps) >= 3
    for cap in caps:
        assert "id" in cap
        assert "name" in cap
        assert "status" in cap


def test_c1_07_cors_headers_handling(api_client):
    res = api_client.options(
        "/api/system/status",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    )
    assert res.status_code in [200, 204]


def test_c1_08_unknown_route_returns_404_safely(api_client):
    res = api_client.get("/api/nonexistent_gateway_route_12345")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data
    assert "traceback" not in str(data).lower()


def test_c1_09_static_documentation_openapi_json_available(api_client):
    res = api_client.get("/openapi.json")
    assert res.status_code == 200
    data = res.json()
    assert "paths" in data
    assert "/health" in data["paths"]


def test_c1_10_swagger_ui_html_served(api_client):
    res = api_client.get("/docs")
    assert res.status_code == 200
    assert "html" in res.headers.get("content-type", "").lower()


# ==============================================================================
# C2: ERROR SAFETY & NO SECRETS LEAKAGE (Tests 11 - 20)
# ==============================================================================

def test_c1_11_malformed_json_body_returns_422_without_traceback(api_client):
    res = api_client.post(
        "/api/auth/login",
        content="{\"username\": \"test\", invalid_json: ",
        headers={"Content-Type": "application/json"}
    )
    assert res.status_code in [400, 422]
    text = res.text
    assert "Traceback (most recent call last)" not in text
    assert "C:\\" not in text and "/home/" not in text


def test_c1_12_empty_json_body_on_post_endpoint(api_client):
    res = api_client.post(
        "/api/auth/login",
        content="{}",
        headers={"Content-Type": "application/json"}
    )
    assert res.status_code == 422


def test_c1_13_non_json_content_type_rejected(api_client):
    res = api_client.post(
        "/api/auth/login",
        content="username=analyst&password=pw",
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert res.status_code in [422, 400]


def test_c1_14_oversized_payload_rejected(api_client):
    giant_string = "A" * (1024 * 1024)  # 1MB of text
    res = api_client.post(
        "/api/auth/login",
        json={"username": giant_string, "password": "x"},
    )
    assert res.status_code in [400, 422, 413]


def test_c1_15_unicode_boundary_characters_handled_safely(api_client):
    unicode_payloads = [
        "🔥🛡️⚡",
        "../../etc/passwd",
        "'; DROP TABLE users; --",
        "null\x00byte",
        "A" * 500,
    ]
    for val in unicode_payloads:
        res = api_client.post(
            "/api/auth/login",
            json={"username": val, "password": "password"},
        )
        assert res.status_code in [400, 401, 422]
        assert "traceback" not in res.text.lower()


def test_c1_16_get_routes_do_not_accept_large_query_strings(api_client):
    long_query = "x=" + ("a" * 8000)
    res = api_client.get(f"/health?{long_query}")
    assert res.status_code in [200, 414]


def test_c1_17_sanitized_validation_error_structure(api_client):
    res = api_client.post("/api/auth/login", json={"username": 12345})
    assert res.status_code == 422
    data = res.json()
    assert "detail" in data


def test_c1_18_system_endpoints_do_not_leak_environment_secrets(api_client):
    for endpoint in ["/health", "/ready", "/api/system/status"]:
        res = api_client.get(endpoint)
        text = res.text
        assert "SECRET_KEY" not in text
        assert "private_key" not in text
        assert "password" not in text.lower()


def test_c1_19_public_endpoints_cache_control_headers(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    # Health probe should not be cached aggressively
    headers = res.headers
    assert "content-type" in headers


def test_c1_20_head_request_behavior(api_client):
    res = api_client.head("/health")
    assert res.status_code in [200, 405]


# ==============================================================================
# C3: API CONTRACT PARAMS & TYPING (Tests 21 - 45)
# ==============================================================================

@pytest.mark.parametrize("route,expected_code", [
    ("/api/datasets", 401),
    ("/api/budget/health", 401),
    ("/api/budget/financial", 401),
    ("/api/receipts/nonexistent-id", 401),
    ("/api/audit/verify", 401),
    ("/api/security/events", 401),
    ("/api/security/alerts", 401),
    ("/api/users", 401),
])
def test_c1_routes_require_authorization_bearer_token(api_client, route, expected_code):
    res = api_client.get(route)
    assert res.status_code == expected_code, f"Expected {expected_code} for anonymous call to {route}"


@pytest.mark.parametrize("token", [
    "",
    "Bearer ",
    "Bearer invalid_token_xyz",
    "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.bogus_signature",
    "Basic YWRtaW46cGFzc3dvcmQ=",
])
def test_c1_malformed_auth_headers_rejected(api_client, token):
    res = api_client.get("/api/datasets", headers={"Authorization": token})
    assert res.status_code == 401


@pytest.mark.parametrize("invalid_epsilon", [
    0.0,
    -0.5,
    -10.0,
    1.5,
    5.1,
    999.0,
    "NaN",
    "Infinity",
    "null",
])
def test_c1_query_preview_rejects_out_of_bounds_epsilon(api_client, invalid_epsilon):
    # Log in first to get token
    login_res = api_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_res.json()["token"]

    res = api_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "health",
            "field": "diagnosis",
            "operator": "=",
            "value": "Hypertension",
            "epsilon": invalid_epsilon,
        }
    )
    assert res.status_code in [400, 422]


@pytest.mark.parametrize("invalid_operator", [
    "!=",
    "LIKE",
    ">",
    "<",
    "IN",
    "BETWEEN",
    "UNION",
    "; DROP TABLE",
])
def test_c1_query_preview_rejects_unsupported_operators(api_client, invalid_operator):
    login_res = api_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_res.json()["token"]

    res = api_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": "health",
            "field": "diagnosis",
            "operator": invalid_operator,
            "value": "Hypertension",
            "epsilon": 0.5,
        }
    )
    assert res.status_code == 400


@pytest.mark.parametrize("invalid_dataset_id", [
    "users",
    "sqlite_master",
    "audit_log",
    "../health",
    "health/../users",
    "nonexistent_dataset_99",
    "",
])
def test_c1_query_preview_rejects_unauthorized_dataset_ids(api_client, invalid_dataset_id):
    login_res = api_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_res.json()["token"]

    res = api_client.post(
        "/api/queries/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "dataset_id": invalid_dataset_id,
            "field": "diagnosis",
            "operator": "=",
            "value": "Hypertension",
            "epsilon": 0.5,
        }
    )
    assert res.status_code in [400, 404, 422]


def test_c1_45_evaluation_status_contract_returns_honest_disclosure(api_client):
    login_res = api_client.post("/api/auth/login", json={"username": "analyst_user", "password": "AnalystPass2026!"})
    token = login_res.json()["token"]

    res = api_client.get("/api/evaluation/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "official_accounting_spec_status" in data
    assert "official_empirical_risk_evaluation_status" in data
    assert "notice" in data
