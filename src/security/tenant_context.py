import re

from .errors import SecurityError
from .models import Principal, TenantContext

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def resolve_tenant_context(
    principal: Principal,
    tenant_selector: str | None,
    environment_selector: str | None,
    request_id: str,
    trace_id: str | None,
) -> tuple[Principal, TenantContext]:
    if tenant_selector and not IDENTIFIER.fullmatch(tenant_selector):
        raise SecurityError("tenant_selector_invalid", "Tenant selector is invalid", status_code=403)
    authorised = {a.tenant_id: a.environments for a in principal.tenant_access}
    if tenant_selector:
        if tenant_selector not in authorised and "*" not in authorised:
            raise SecurityError("tenant_access_denied", "Tenant access is denied", status_code=403)
        tenant = tenant_selector
    elif len({key for key in authorised if key != "*"}) == 1:
        tenant = next(key for key in authorised if key != "*")
    else:
        raise SecurityError("tenant_selection_required", "An explicit authorised tenant is required", status_code=400)
    environments = authorised.get(tenant, authorised.get("*", frozenset()))
    if environment_selector and (
        not IDENTIFIER.fullmatch(environment_selector) or environment_selector not in environments
    ):
        raise SecurityError("environment_access_denied", "Environment access is denied", status_code=403)
    environment = environment_selector or (next(iter(environments)) if len(environments) == 1 else None)
    if len(environments) > 1 and environment is None:
        raise SecurityError(
            "environment_selection_required", "An explicit authorised environment is required", status_code=400
        )
    active = principal.with_context(tenant, environment)
    return active, TenantContext(tenant, environment, principal.subject, request_id, trace_id)
