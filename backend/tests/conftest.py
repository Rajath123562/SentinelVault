"""Pytest fixtures for HOTFIX backend tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_application
from app.core.config import get_settings


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
