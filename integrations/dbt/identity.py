"""Deterministic provider-to-canonical identity mappings."""

from hashlib import sha256


def resource_id(tenant: str, environment: str, project: str, resource_type: str, unique_id: str) -> str:
    scope = "\x1f".join((tenant, environment, project, resource_type, unique_id))
    return "dbt_" + sha256(scope.encode()).hexdigest()


def asset_identity(tenant: str, environment: str, project: str, resource_type: str, unique_id: str) -> str | None:
    if resource_type not in {"model", "source", "seed", "snapshot"}:
        return None
    return resource_id(tenant, environment, project, resource_type, unique_id)


def run_identity(tenant: str, environment: str, project: str, invocation_id: str) -> str:
    return resource_id(tenant, environment, project, "invocation", invocation_id)
