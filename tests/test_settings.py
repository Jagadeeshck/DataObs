from __future__ import annotations

import textwrap

import pytest

from src.config.settings import ConfigurationError, load_settings


def test_default_development_settings(monkeypatch):
    monkeypatch.delenv("DATAOBS_ENV", raising=False)
    monkeypatch.delenv("DATAOBS_CONFIG", raising=False)
    settings = load_settings()
    assert settings.runtime.env == "development"
    assert settings.store_backend == "memory"


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("DATAOBS_ENV", "development")
    monkeypatch.setenv("API_PORT", "9999")
    settings = load_settings()
    assert settings.port == 9999


def test_dataobs_config_yaml_loading(monkeypatch, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(textwrap.dedent('''
    api:
      port: 8123
    tenant:
      id: yaml-tenant
    '''))
    monkeypatch.setenv("DATAOBS_CONFIG", str(cfg))
    settings = load_settings()
    assert settings.port == 8123
    assert settings.tenant_id == "yaml-tenant"


def test_production_rejects_missing_api_token(monkeypatch):
    monkeypatch.setenv("DATAOBS_ENV", "production")
    monkeypatch.delenv("API_TOKEN", raising=False)
    with pytest.raises(ConfigurationError, match="API_TOKEN"):
        load_settings()


def test_production_rejects_memory_backend(monkeypatch):
    monkeypatch.setenv("DATAOBS_ENV", "production")
    monkeypatch.setenv("API_TOKEN", "token")
    monkeypatch.setenv("DATAOBS_ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("DATAOBS_STORE_BACKEND", "memory")
    with pytest.raises(ConfigurationError, match="memory"):
        load_settings()


def test_production_rejects_default_password(monkeypatch):
    monkeypatch.setenv("DATAOBS_ENV", "production")
    monkeypatch.setenv("API_TOKEN", "token")
    monkeypatch.setenv("DATAOBS_ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("DATAOBS_STORE_BACKEND", "elasticsearch")
    monkeypatch.setenv("DATAOBS_TENANT_ID", "acme")
    monkeypatch.setenv("ELASTICSEARCH_PASSWORD", "changeme")
    with pytest.raises(ConfigurationError, match="default"):
        load_settings()


def test_poc_mode_compatibility(monkeypatch):
    monkeypatch.setenv("DATAOBS_ENV", "poc")
    settings = load_settings()
    assert settings.runtime.env == "poc"


def test_app_can_build_with_injected_settings():
    from src.api.app import create_app
    from src.config.settings import APISettings, AppSettings, AuthSettings, ElasticsearchSettings, ObservabilitySettings, RuntimeSettings, TenantSettings

    settings = AppSettings(
        runtime=RuntimeSettings(env="test"),
        api=APISettings(),
        elasticsearch=ElasticsearchSettings(),
        auth=AuthSettings(api_token=None),
        tenant=TenantSettings(),
        observability=ObservabilitySettings(),
        store_backend="memory",
    )
    app = create_app(settings=settings)
    assert app.title == "DataObs API"
