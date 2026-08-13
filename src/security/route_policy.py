"""Anchored, method-aware API permission policy.

Patterns describe route *templates*, never caller-controlled concrete URLs.  New API
families therefore fail closed until deliberately registered here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .permissions import Permission

PUBLIC_ROUTES = frozenset(
    {("GET", "/livez"), ("GET", "/startupz"), ("GET", "/readyz"), ("GET", "/health"), ("GET", "/api/v1/auth/config")}
)

# Legacy templates are deliberately enumerated while the API converges on /api/v1.
EXPLICIT_ROUTES = {
    ("POST", "/api/v1/incident-automation/approvals"): Permission.WORKFLOWS_EXECUTE,
    ("POST", "/api/v1/incident-automation/approvals/{approval_id}/approve"): Permission.WORKFLOWS_APPROVE,
    ("POST", "/api/v1/incident-automation/approvals/{approval_id}/reject"): Permission.WORKFLOWS_APPROVE,
    ("POST", "/api/v1/incident-automation/executions"): Permission.WORKFLOWS_EXECUTE,
    ("POST", "/api/v1/approvals/{approval_id}/approve"): Permission.WORKFLOWS_APPROVE,
    ("POST", "/api/v1/approvals/{approval_id}/reject"): Permission.WORKFLOWS_APPROVE,
    ("GET", "/rules"): Permission.QUALITY_READ,
    ("POST", "/rules"): Permission.QUALITY_WRITE,
    ("DELETE", "/rules/{rule_id}"): Permission.QUALITY_WRITE,
    ("GET", "/quality/results"): Permission.QUALITY_READ,
    ("GET", "/quality/results/{result_id}"): Permission.QUALITY_READ,
    ("POST", "/quality/results"): Permission.QUALITY_WRITE,
    ("GET", "/lineage/nodes"): Permission.LINEAGE_READ,
    ("GET", "/lineage/edges"): Permission.LINEAGE_READ,
    ("GET", "/lineage/impact/{node_id:path}"): Permission.LINEAGE_READ,
    ("POST", "/api/data-observability/assets"): Permission.ASSETS_WRITE,
    ("GET", "/api/data-observability/assets"): Permission.ASSETS_READ,
    ("GET", "/api/data-observability/assets/{asset_id:path}"): Permission.ASSETS_READ,
    ("GET", "/api/data-observability/assets/{asset_id:path}/lineage"): Permission.LINEAGE_READ,
    ("GET", "/api/data-observability/assets/{asset_id:path}/health"): Permission.ASSETS_READ,
    ("POST", "/api/data-observability/assets/{asset_id:path}/columns"): Permission.ASSETS_WRITE,
    ("POST", "/api/data-observability/quality-checks"): Permission.QUALITY_WRITE,
    ("POST", "/api/data-observability/quality-runs"): Permission.QUALITY_EXECUTE,
    ("GET", "/api/data-observability/quality-runs"): Permission.QUALITY_READ,
    ("POST", "/api/data-observability/job-runs"): Permission.JOBS_EXECUTE,
    ("GET", "/api/data-observability/job-runs"): Permission.JOBS_READ,
    ("POST", "/api/v1/lineage"): Permission.COLLECTION_INGEST,
    ("GET", "/api/v1/datasets/{namespace}/{name:path}"): Permission.ASSETS_READ,
    ("GET", "/api/v1/migrations"): Permission.PLATFORM_ADMIN,
    ("POST", "/api/v1/scan-policies"): Permission.COLLECTION_MANAGE,
    ("GET", "/api/v1/scan-policies"): Permission.COLLECTION_MANAGE,
    ("POST", "/api/v1/pathway-explorer/search"): Permission.LINEAGE_READ,
    ("GET", "/api/v1/entities/{node_id}/summary"): Permission.ASSETS_READ,
    ("GET", "/api/v1/events/stream"): Permission.AUTH_READ,
    ("GET", "/strategy/enterprise-backlog"): Permission.PLATFORM_ADMIN,
    ("GET", "/api/v1/platform/{section}"): Permission.PLATFORM_OPERATIONS_READ,
}


@dataclass(frozen=True)
class RouteRule:
    methods: frozenset[str]
    pattern: re.Pattern[str]
    read: Permission
    write: Permission

    @property
    def name(self) -> str:
        return f"{','.join(sorted(self.methods))}:{self.pattern.pattern}"


def _rule(methods: str, pattern: str, read: Permission, write: Permission | None = None) -> RouteRule:
    return RouteRule(frozenset(methods.split()), re.compile(r"^" + pattern + r"$"), read, write or read)


RULES = (
    _rule("GET HEAD", r"/api/v1/dbt(?:/.*)?", Permission.JOBS_READ),
    _rule("POST", r"/api/v1/dbt/artifacts", Permission.COLLECTION_INGEST),
    _rule("GET HEAD", r"/api/v1/platform/environments(?:/\{environment_id\})?", Permission.ENVIRONMENTS_READ),
    _rule("POST", r"/api/v1/platform/environments", Permission.ENVIRONMENTS_WRITE),
    _rule("POST", r"/api/v1/platform/environments/\{environment_id\}/transition", Permission.ENVIRONMENTS_WRITE),
    _rule("GET HEAD", r"/api/v1/platform/clusters(?:/\{cluster_id\})?", Permission.CLUSTERS_READ),
    _rule("POST", r"/api/v1/platform/clusters/register", Permission.CLUSTERS_REGISTER),
    _rule("GET HEAD", r"/api/v1/platform/installations(?:/\{installation_id\})?", Permission.INSTALLATIONS_READ),
    _rule("POST", r"/api/v1/platform/installations", Permission.INSTALLATIONS_MANAGE),
    _rule(
        "GET HEAD",
        r"/api/v1/platform/tenants(?:/\{tenant_id\}(?:/offboarding-preview)?)?",
        Permission.TENANTS_PROVISION,
    ),
    _rule("POST", r"/api/v1/platform/tenants", Permission.TENANTS_PROVISION),
    _rule("POST", r"/api/v1/platform/tenants/\{tenant_id\}/\{action\}", Permission.TENANTS_PROVISION),
    _rule("GET HEAD", r"/api/v1/platform/(?:fleet|drift|capacity)", Permission.PLATFORM_OPERATIONS_READ),
    _rule("POST", r"/api/v1/platform/deployment-plans", Permission.INSTALLATIONS_MANAGE),
    _rule("POST", r"/api/v1/platform/deployment-plans/\{plan_id\}/transition", Permission.INSTALLATIONS_MANAGE),
    _rule("POST", r"/api/v1/platform/promotions", Permission.PLATFORM_PROMOTIONS_EXECUTE),
    _rule("GET", r"/api/v1/auth/me", Permission.AUTH_READ),
    _rule("GET", r"/api/v1/iam/role-bindings(?:/\{binding_id\})?", Permission.IAM_READ),
    _rule("POST PATCH DELETE", r"/api/v1/iam/role-bindings(?:/\{binding_id\})?", Permission.IAM_WRITE),
    _rule("GET", r"/api/v1/iam/effective-access/me", Permission.AUTH_READ),
    _rule("GET", r"/api/v1/iam/effective-access/\{principal_reference\}", Permission.EFFECTIVE_ACCESS_READ),
    _rule("GET", r"/api/v1/iam/audit-events", Permission.AUDIT_READ),
    _rule("GET", r"/api/v1/iam/service-principals(?:/\{service_principal_id\})?", Permission.SERVICE_PRINCIPALS_READ),
    _rule(
        "POST PATCH",
        r"/api/v1/iam/service-principals(?:/\{service_principal_id\}(?:/(?:suspend|reactivate|revoke))?)?",
        Permission.SERVICE_PRINCIPALS_WRITE,
    ),
    _rule("GET", r"/api/v1/iam/break-glass/requests(?:/\{request_id\})?", Permission.BREAK_GLASS_REQUEST),
    _rule("POST", r"/api/v1/iam/break-glass/requests", Permission.BREAK_GLASS_REQUEST),
    _rule(
        "POST", r"/api/v1/iam/break-glass/requests/\{request_id\}/(?:approve|reject)", Permission.BREAK_GLASS_APPROVE
    ),
    _rule("POST", r"/api/v1/iam/break-glass/requests/\{request_id\}/activate", Permission.BREAK_GLASS_ACTIVATE),
    _rule(
        "POST",
        r"/api/v1/iam/break-glass/requests/\{request_id\}/(?:revoke|review|close)",
        Permission.BREAK_GLASS_REVOKE,
    ),
    _rule("GET", r"/api/v1/platform/credentials(?:/\{credential_id\})?", Permission.CREDENTIALS_READ),
    _rule("GET", r"/api/v1/platform/credential-rotations(?:/\{rotation_id\})?", Permission.CREDENTIALS_READ),
    _rule("POST", r"/api/v1/platform/credential-rotations", Permission.CREDENTIALS_ROTATE),
    _rule("POST", r"/api/v1/platform/credential-rotations/\{rotation_id\}/approve", Permission.CREDENTIALS_APPROVE),
    _rule(
        "POST",
        r"/api/v1/platform/credential-rotations/\{rotation_id\}/(?:stage|verify|promote|rollback|retire|complete)",
        Permission.CREDENTIALS_ROTATE,
    ),
    _rule(
        "POST",
        r"/(?:api/v1/openlineage/events|api/v1/lineage|api/data-observability/lineage/events)",
        Permission.COLLECTION_INGEST,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:assets|command-center|topology|pillars?)(?:/.*)?", Permission.ASSETS_READ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:assets|command-center|topology|pillars?)(?:/.*)?",
        Permission.ASSETS_READ,
        Permission.ASSETS_WRITE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:lineage|pathways?)(?:/.*)?", Permission.LINEAGE_READ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:lineage|pathways?)(?:/.*)?",
        Permission.LINEAGE_READ,
        Permission.LINEAGE_WRITE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:quality|rules?)(?:/.*)?", Permission.QUALITY_READ),
    _rule("POST", r"/api(?:/v1)?/(?:quality|rules?)(?:/.*)?/(?:run|executions?)", Permission.QUALITY_EXECUTE),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:quality|rules?)(?:/.*)?",
        Permission.QUALITY_READ,
        Permission.QUALITY_WRITE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:monitors?|baselines?)(?:/.*)?", Permission.MONITORS_READ),
    _rule("POST", r"/api(?:/v1)?/monitors?(?:/.*)?/run", Permission.MONITORS_EXECUTE),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:monitors?|baselines?)(?:/.*)?",
        Permission.MONITORS_READ,
        Permission.MONITORS_WRITE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/data-products?(?:/.*)?", Permission.DATA_PRODUCTS_READ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/data-products?(?:/.*)?",
        Permission.DATA_PRODUCTS_READ,
        Permission.DATA_PRODUCTS_WRITE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:jobs?|runs?)(?:/.*)?", Permission.JOBS_READ),
    _rule(
        "POST PUT PATCH DELETE", r"/api(?:/v1)?/(?:jobs?|runs?)(?:/.*)?", Permission.JOBS_READ, Permission.JOBS_EXECUTE
    ),
    _rule(
        "GET HEAD",
        r"/api(?:/v1)?/(?:streams?|stream-connectors?|stream-intelligence|stream-detectors?|kafka|topics?|connectors?|schemas?)(?:/.*)?",
        Permission.STREAMS_READ,
    ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:streams?|stream-connectors?|stream-intelligence|stream-detectors?|kafka|topics?|connectors?|schemas?)(?:/.*)?",
        Permission.STREAMS_READ,
        Permission.STREAMS_EXECUTE,
    ),
    _rule(
        "GET HEAD",
        r"/api(?:/v1)?/(?:incidents?|findings?|incident-correlation|incident-floods|incident-automation)(?:/.*)?",
        Permission.INCIDENTS_READ,
    ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:incidents?|findings?)(?:/.*)?",
        Permission.INCIDENTS_READ,
        Permission.INCIDENTS_WRITE,
    ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/incident-automation(?:/.*)?",
        Permission.INCIDENTS_READ,
        Permission.WORKFLOWS_APPROVE,
    ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:workflows?|actions?)(?:/.*)?/(?:approve|reject|approvals?/.*)",
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_APPROVE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:workflows?|actions?)(?:/.*)?", Permission.WORKFLOWS_READ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:workflows?|actions?)(?:/.*)?",
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_EXECUTE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:integrations?|sources?)(?:/.*)?", Permission.INTEGRATIONS_READ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:integrations?|sources?)(?:/.*)?",
        Permission.INTEGRATIONS_READ,
        Permission.INTEGRATIONS_WRITE,
    ),
    _rule(
        "GET POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:collectors?|scanners?|scan-tasks?|tenants?)(?:/.*)?",
        Permission.COLLECTION_MANAGE,
    ),
)

# Stable public name consumed by repository-policy checks.
ROUTE_RULES = RULES


def matching_rule(method: str, route_template: str) -> RouteRule | None:
    """Return the single classification rule, including explicit legacy routes."""
    method = method.upper()
    explicit = EXPLICIT_ROUTES.get((method, route_template))
    if explicit is not None:
        return _rule(method, re.escape(route_template), explicit)
    matches = [rule for rule in RULES if method in rule.methods and rule.pattern.fullmatch(route_template)]
    return matches[0] if len(matches) == 1 else None


def permission_for_route(method: str, route_template: str) -> Permission | None:
    method = method.upper()
    if (method, route_template) in PUBLIC_ROUTES:
        raise LookupError(f"public routes have no permission: {method} {route_template}")
    if (method, route_template) in EXPLICIT_ROUTES:
        return EXPLICIT_ROUTES[(method, route_template)]
    matches = [rule for rule in RULES if method in rule.methods and rule.pattern.fullmatch(route_template)]
    if len(matches) != 1:
        if not matches:
            raise LookupError(f"no permission policy for {method} {route_template}")
        raise LookupError(f"ambiguous permission policy for {method} {route_template}")
    return matches[0].read if method in {"GET", "HEAD"} else matches[0].write


def validate_policy() -> None:
    for method, path in PUBLIC_ROUTES:
        if any(method in rule.methods and rule.pattern.fullmatch(path) for rule in RULES):
            raise RuntimeError(f"public route is also protected: {method} {path}")


# Backward-compatible alias.
permission_for = permission_for_route
