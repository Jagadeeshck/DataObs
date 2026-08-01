"""Anchored, method-aware API permission policy.

Patterns describe route *templates*, never caller-controlled concrete URLs.  New API
families therefore fail closed until deliberately registered here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .permissions import Permission

PUBLIC_ROUTES = frozenset({("GET", "/livez"), ("GET", "/readyz"), ("GET", "/health"), ("GET", "/api/v1/auth/config")})

# Legacy templates are deliberately enumerated while the API converges on /api/v1.
EXPLICIT_ROUTES = {
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
}


@dataclass(frozen=True)
class RouteRule:
    methods: frozenset[str]
    pattern: re.Pattern[str]
    read: Permission
    write: Permission


def _rule(methods: str, pattern: str, read: Permission, write: Permission | None = None) -> RouteRule:
    return RouteRule(frozenset(methods.split()), re.compile(r"^" + pattern + r"$"), read, write or read)


RULES = (
    _rule("GET", r"/api/v1/auth/me", Permission.AUTH_READ),
    _rule("GET", r"/api/v1/iam/role-bindings(?:/\{binding_id\})?", Permission.IAM_READ),
    _rule("POST PATCH DELETE", r"/api/v1/iam/role-bindings(?:/\{binding_id\})?", Permission.IAM_WRITE),
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
        r"/api(?:/v1)?/(?:streams?|stream-connectors?|kafka|topics?|connectors?|schemas?)(?:/.*)?",
        Permission.STREAMS_READ,
    ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:streams?|stream-connectors?|kafka|topics?|connectors?|schemas?)(?:/.*)?",
        Permission.STREAMS_READ,
        Permission.STREAMS_EXECUTE,
    ),
    _rule("GET HEAD", r"/api(?:/v1)?/(?:incidents?|findings?)(?:/.*)?", Permission.INCIDENTS_READ),
    _rule(
        "POST PUT PATCH DELETE",
        r"/api(?:/v1)?/(?:incidents?|findings?)(?:/.*)?",
        Permission.INCIDENTS_READ,
        Permission.INCIDENTS_WRITE,
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


def permission_for_route(method: str, route_template: str) -> Permission | None:
    method = method.upper()
    if (method, route_template) in PUBLIC_ROUTES:
        return None
    if (method, route_template) in EXPLICIT_ROUTES:
        return EXPLICIT_ROUTES[(method, route_template)]
    matches = [rule for rule in RULES if method in rule.methods and rule.pattern.fullmatch(route_template)]
    if len(matches) != 1:
        raise LookupError(f"route permission policy has {len(matches)} matches for {method} {route_template}")
    return matches[0].read if method in {"GET", "HEAD"} else matches[0].write


def validate_policy() -> None:
    for method, path in PUBLIC_ROUTES:
        if any(method in rule.methods and rule.pattern.fullmatch(path) for rule in RULES):
            raise RuntimeError(f"public route is also protected: {method} {path}")
