from dataclasses import replace

import pytest

from services.security.audit_repository import SECURITY_EVENT_DATA_STREAM
from services.security.role_binding_repository import ROLE_BINDING_ALIAS, RoleBinding
from src.config.settings import ConfigurationError, load_settings
from src.security.redaction import redact
from src.security.route_policy import permission_for


def test_released_migration_resources_are_fixed():
    assert ROLE_BINDING_ALIAS == "dataobs-role-bindings-v1"
    assert SECURITY_EVENT_DATA_STREAM.startswith("logs-dataobs.security-event-")


def test_binding_id_is_deterministic_and_scoped():
    args = dict(
        issuer="https://id.example",
        principal_type="service",
        principal_id="collector",
        tenant_id="tenant-a",
        environments=("prod",),
        roles=("collector",),
        description="",
        actor="admin",
    )
    assert RoleBinding.new(**args).binding_id == RoleBinding.new(**args).binding_id
    assert RoleBinding.new(**args).binding_id != RoleBinding.new(**(args | {"tenant_id": "tenant-b"})).binding_id


def test_redaction_preserves_safe_metadata():
    value = redact(
        {
            "authorization": "Bearer abc",
            "password": "bad",
            "token_expiry": "soon",
            "nested": {"client_secret": "bad", "secret_reference_name": "oidc"},
        }
    )
    assert "abc" not in repr(value) and "bad" not in repr(value)
    assert value["token_expiry"] == "soon"
    assert value["nested"]["secret_reference_name"] == "oidc"


def test_route_policy_is_method_aware_and_exact():
    assert permission_for("GET", "/api/v1/iam/role-bindings").value == "iam:read"
    assert permission_for("POST", "/api/v1/iam/role-bindings").value == "iam:write"
    with pytest.raises(LookupError):
        permission_for("GET", "/api/v1/iam/role-bindings/not-a-template")


def test_production_rejects_claims_only(monkeypatch):
    monkeypatch.setenv("DATAOBS_ENV", "production")
    monkeypatch.setenv("API_TOKEN", "temporary")
    monkeypatch.setenv("DATAOBS_STORE_BACKEND", "elasticsearch")
    monkeypatch.setenv("ELASTICSEARCH_URL", "https://elastic.example:9200")
    monkeypatch.setenv("ELASTICSEARCH_PASSWORD", "not-a-default")
    monkeypatch.setenv("DATAOBS_AUTH_PROVIDER", "oidc")
    monkeypatch.setenv("DATAOBS_OIDC_ISSUER", "https://identity.example")
    monkeypatch.setenv("DATAOBS_OIDC_AUDIENCE", "dataobs-api")
    monkeypatch.setenv("DATAOBS_OIDC_ALLOWED_ALGORITHMS", "RS256")
    monkeypatch.setenv("DATAOBS_OIDC_PLATFORM_ADMIN_GROUPS", "platform-admins")
    monkeypatch.setenv("DATAOBS_ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("DATAOBS_AUTHORIZATION_SOURCE", "claims")
    with pytest.raises(ConfigurationError, match="claims-only|bindings or intersection"):
        load_settings()
