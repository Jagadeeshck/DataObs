from dataclasses import replace

import pytest

from src.config.settings import AuthSettings, OIDCSettings
from src.security.authentication import principal_from_claims
from src.security.errors import SecurityError
from src.security.permissions import Permission
from src.security.roles import ROLE_PERMISSIONS, permissions_for_roles
from src.security.tenant_context import resolve_tenant_context

SETTINGS = AuthSettings(
    provider="oidc",
    oidc=OIDCSettings(
        issuer="https://identity.example.test/realms/dataobs",
        audience="dataobs-api",
        group_role_mappings={"dataobs-viewers": ("viewer",), "collectors": ("collector",)},
        platform_admin_groups=frozenset({"dataobs-platform-admins"}),
    ),
)


def claims(groups=None, access=None):
    return {
        "sub": "subject-1",
        "iss": SETTINGS.oidc.issuer,
        "groups": groups or ["dataobs-viewers"],
        "dataobs_access": access or [{"tenant_id": "tenant-a", "environments": ["production"]}],
    }


def test_role_registry_is_fail_closed_and_collector_is_ingestion_only():
    assert set(ROLE_PERMISSIONS) == {
        "platform_admin",
        "tenant_admin",
        "operator",
        "investigator",
        "monitor_editor",
        "workflow_approver",
        "viewer",
        "collector",
    }
    assert permissions_for_roles(frozenset({"unknown"})) == frozenset()
    collector = permissions_for_roles(frozenset({"collector"}))
    assert Permission.COLLECTION_INGEST in collector
    assert Permission.ASSETS_READ not in collector and Permission.IAM_WRITE not in collector
    assert Permission.WORKFLOWS_APPROVE not in ROLE_PERMISSIONS["operator"]
    assert Permission.IAM_WRITE not in ROLE_PERMISSIONS["monitor_editor"]


def test_claim_roles_are_not_trusted_and_group_mapping_is_explicit():
    principal = principal_from_claims({**claims(), "dataobs_roles": ["platform_admin"]}, SETTINGS)
    assert principal.roles == frozenset({"viewer"})
    assert Permission.PLATFORM_ADMIN not in principal.permissions


def test_tenant_and_environment_selectors_only_narrow_authorised_access():
    principal = principal_from_claims(claims(), SETTINGS)
    active, context = resolve_tenant_context(principal, None, None, "request-1", None)
    assert (context.tenant_id, context.environment) == ("tenant-a", "production")
    assert active.active_tenant == "tenant-a"
    with pytest.raises(SecurityError, match="Tenant access is denied") as denied:
        resolve_tenant_context(principal, "tenant-b", "production", "request-2", None)
    assert denied.value.status_code == 403
    with pytest.raises(SecurityError, match="Environment access is denied"):
        resolve_tenant_context(principal, "tenant-a", "staging", "request-3", None)


def test_multi_tenant_and_multi_environment_require_explicit_selection():
    principal = principal_from_claims(
        claims(
            access=[
                {"tenant_id": "tenant-a", "environments": ["production", "staging"]},
                {"tenant_id": "tenant-b", "environments": ["production"]},
            ]
        ),
        SETTINGS,
    )
    with pytest.raises(SecurityError) as missing_tenant:
        resolve_tenant_context(principal, None, None, "request-1", None)
    assert missing_tenant.value.reason_code == "tenant_selection_required"
    with pytest.raises(SecurityError) as missing_environment:
        resolve_tenant_context(principal, "tenant-a", None, "request-1", None)
    assert missing_environment.value.reason_code == "environment_selection_required"


@pytest.mark.parametrize("value", ["bad tenant", "../tenant", "", "a" * 129])
def test_malformed_tenant_claim_or_selector_fails_closed(value):
    principal = principal_from_claims(claims(), SETTINGS)
    if value:
        with pytest.raises(SecurityError):
            resolve_tenant_context(principal, value, None, "request", None)
