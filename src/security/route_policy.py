"""Authoritative, deny-by-default permission policy for the public v1 API."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .permissions import Permission


@dataclass(frozen=True)
class RouteRule:
    name: str
    pattern: re.Pattern[str]
    read: Permission
    write: Permission


PUBLIC_ROUTES = frozenset({("GET", "/api/v1/auth/config")})

# Rules describe route *templates*, not caller-controlled request paths.  More
# specific high-risk routes are intentionally evaluated first.
ROUTE_RULES = (
    RouteRule("auth-self", re.compile(r"^/api/v1/auth/me$"), Permission.AUTH_READ, Permission.AUTH_READ),
    RouteRule("iam", re.compile(r"^/api/v1/iam(?:/|$)"), Permission.IAM_READ, Permission.IAM_WRITE),
    RouteRule(
        "collector-ingest",
        re.compile(r"^/api/v1/(?:openlineage/events|lineage)$"),
        Permission.COLLECTION_INGEST,
        Permission.COLLECTION_INGEST,
    ),
    RouteRule(
        "workflow-approvals",
        re.compile(r"^/api/v1/approvals/[^/]+/(?:approve|reject)$"),
        Permission.WORKFLOWS_APPROVE,
        Permission.WORKFLOWS_APPROVE,
    ),
    RouteRule(
        "incident-actions",
        re.compile(r"^/api/v1/incidents/[^/]+/(?:run-workflow|actions)(?:/|$)"),
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_EXECUTE,
    ),
    RouteRule(
        "incidents",
        re.compile(r"^/api/v1/(?:incidents|findings)(?:/|$)"),
        Permission.INCIDENTS_READ,
        Permission.INCIDENTS_WRITE,
    ),
    RouteRule(
        "lineage",
        re.compile(r"^/api/v1/(?:lineage|datasets)(?:/|$)"),
        Permission.LINEAGE_READ,
        Permission.LINEAGE_WRITE,
    ),
    RouteRule("jobs", re.compile(r"^/api/v1/(?:jobs|runs)(?:/|$)"), Permission.JOBS_READ, Permission.JOBS_EXECUTE),
    RouteRule(
        "streams",
        re.compile(r"^/api/v1/(?:kafka|streams|topics|connectors|schemas)(?:/|$)"),
        Permission.STREAMS_READ,
        Permission.STREAMS_EXECUTE,
    ),
    RouteRule(
        "assets",
        re.compile(r"^/api/v1/(?:assets|entities|topology|command-center|pillars)(?:/|$)"),
        Permission.ASSETS_READ,
        Permission.ASSETS_WRITE,
    ),
    RouteRule("pathways", re.compile(r"^/api/v1/pathway(?:-|/|$)"), Permission.LINEAGE_READ, Permission.LINEAGE_WRITE),
    RouteRule("audit-events", re.compile(r"^/api/v1/events(?:/|$)"), Permission.AUDIT_READ, Permission.AUDIT_READ),
    RouteRule(
        "integrations",
        re.compile(r"^/api/v1/(?:integrations|sources)(?:/|$)"),
        Permission.INTEGRATIONS_READ,
        Permission.INTEGRATIONS_WRITE,
    ),
    RouteRule(
        "collection-admin",
        re.compile(r"^/api/v1/(?:tenants|collectors|scanners|scan-policies)(?:/|$)"),
        Permission.COLLECTION_MANAGE,
        Permission.COLLECTION_MANAGE,
    ),
    RouteRule("migrations", re.compile(r"^/api/v1/migrations$"), Permission.PLATFORM_ADMIN, Permission.PLATFORM_ADMIN),
)


def matching_rule(method: str, route_template: str) -> RouteRule | None:
    if (method.upper(), route_template) in PUBLIC_ROUTES:
        return None
    return next((rule for rule in ROUTE_RULES if rule.pattern.search(route_template)), None)


def permission_for_route(method: str, route_template: str) -> Permission:
    """Return an explicit permission, refusing unknown or public routes."""
    if (method.upper(), route_template) in PUBLIC_ROUTES:
        raise LookupError("public routes do not have a protected permission")
    rule = matching_rule(method, route_template)
    if rule is None:
        raise LookupError(f"route has no permission policy: {method.upper()} {route_template}")
    return rule.read if method.upper() in {"GET", "HEAD", "OPTIONS"} else rule.write
