"""Tests for B05 (Config validation), B06 (Privacy release default), B07 (Missing spec), and B08 (Invalid spec)."""

import pytest
import yaml
from pathlib import Path
from app.core.config import Settings, ApplicationSettings, SpecSettings


def test_b05_valid_configuration_accepted(app_settings: Settings):
    """B05: Valid application configuration loads and parses cleanly."""
    assert app_settings.app_config.app.short_name == "HOTFIX"
    assert app_settings.app_config.app.team_id == "UG 59"
    assert app_settings.app_config.server.port == 8000
    assert "http://localhost:5173" in app_settings.app_config.server.cors_origins


def test_b05_malformed_configuration_rejected(tmp_path: Path):
    """B05: Malformed YAML configuration is rejected with a clear error."""
    malformed_app = tmp_path / "app_bad.yaml"
    malformed_app.write_text("app: [unterminated list", encoding="utf-8")

    spec_valid = tmp_path / "spec.yaml"
    spec_valid.write_text("""
spec:
  status: NOT_CONFIGURED
privacy: {}
release:
  enabled: false
""", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed YAML"):
        Settings(app_yaml_path=malformed_app, spec_yaml_path=spec_valid)


def test_b05_invalid_port_rejected(tmp_path: Path):
    """B05: Server port outside [1, 65535] is rejected."""
    bad_port_app = tmp_path / "bad_port.yaml"
    bad_port_app.write_text("""
app:
  name: "HOTFIX"
  short_name: "HOTFIX"
  team_id: "UG 59"
  phase: "Phase 1"
  version: "0.1.0"
  config_version: "1.0.0"
server:
  port: 999999
database:
  enabled: false
logging:
  level: "INFO"
privacy_release:
  enabled: false
""", encoding="utf-8")

    spec_valid = tmp_path / "spec.yaml"
    spec_valid.write_text("""
spec:
  status: NOT_CONFIGURED
privacy: {}
release:
  enabled: false
""", encoding="utf-8")

    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        Settings(app_yaml_path=bad_port_app, spec_yaml_path=spec_valid)


def test_b06_privacy_release_disabled_by_default(app_settings: Settings):
    """B06: Privacy releases remain strictly disabled in default Phase 1 configuration."""
    assert app_settings.app_config.privacy_release.enabled is False
    assert app_settings.spec_config.release.enabled is False
    assert app_settings.is_privacy_release_ready is False


def test_b07_missing_or_unconfigured_spec_prevents_release(tmp_path: Path):
    """
    B07: Attempting to enable privacy releases while the specification
    remains NOT_CONFIGURED must trigger a security violation and fail closed.
    """
    app_yaml = tmp_path / "app_enabled.yaml"
    app_yaml.write_text("""
app:
  name: "HOTFIX"
  short_name: "HOTFIX"
  team_id: "UG 59"
  phase: "Phase 1"
  version: "0.1.0"
  config_version: "1.0.0"
server:
  port: 8000
database:
  enabled: false
logging:
  level: "INFO"
privacy_release:
  enabled: true
""", encoding="utf-8")

    unconfigured_spec = tmp_path / "spec_unconfigured.yaml"
    unconfigured_spec.write_text("""
spec:
  status: "NOT_CONFIGURED"
  version: null
privacy:
  unit_of_privacy: null
  accounting_method: null
  cap_epsilon: null
release:
  enabled: false
""", encoding="utf-8")

    with pytest.raises(ValueError, match="Security Violation: Cannot enable privacy releases"):
        Settings(app_yaml_path=app_yaml, spec_yaml_path=unconfigured_spec)


def test_b08_invalid_specification_rejected_or_fails_closed(tmp_path: Path):
    """
    B08: Inconsistent or invalid specification parameters (e.g. negative epsilon cap)
    are rejected during validation.
    """
    invalid_spec = tmp_path / "spec_invalid.yaml"
    invalid_spec.write_text("""
spec:
  status: "NOT_CONFIGURED"
privacy:
  cap_epsilon: -1.5
release:
  enabled: false
""", encoding="utf-8")

    app_valid = tmp_path / "app.yaml"
    app_valid.write_text("""
app:
  name: "HOTFIX"
  short_name: "HOTFIX"
  team_id: "UG 59"
  phase: "Phase 1"
  version: "0.1.0"
  config_version: "1.0.0"
server:
  port: 8000
database:
  enabled: false
logging:
  level: "INFO"
privacy_release:
  enabled: false
""", encoding="utf-8")

    with pytest.raises(ValueError, match="Cumulative epsilon cap must be strictly positive"):
        Settings(app_yaml_path=app_valid, spec_yaml_path=invalid_spec)

