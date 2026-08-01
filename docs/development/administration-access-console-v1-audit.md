# Administration and access Console v1 contract audit

**Audited base:** `043a4e3` (PR #212, Console self-observability). The supplied checkout has no Git remote or local `main` reference, so the immutable base could be inspected but not pulled. No merges after #212 were present. Preflight marker, ownership, generated-artifact, and documentation checks passed.

## Shipped HTTP contracts

Only routes registered in `src/api/app.py` and represented by `openapi.json` are treated as available.

| Contract                                 | Methods | Permission  | Contract notes                                                                                                                                                    |
| ---------------------------------------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/api/v1/auth/me`                        | GET     | `auth:read` | Trusted subject, display name, principal type, roles, permissions, authorised tenant/environment access, active scope, provider, expiry. No raw claims or tokens. |
| `/api/v1/iam/role-bindings`              | GET     | `iam:read`  | Returns `{items}` for the trusted request tenant. No filter, sort, limit, cursor, total, or environment query contract.                                           |
| `/api/v1/iam/role-bindings`              | POST    | `iam:write` | Body: issuer; `user`, `group`, or `service` principal type; principal ID; tenant ID; environment array; role array; optional description. Returns binding.        |
| `/api/v1/iam/role-bindings/{binding_id}` | GET     | `iam:read`  | Tenant-bounded opaque detail lookup.                                                                                                                              |
| same                                     | PATCH   | `iam:write` | Optional environments, roles, active, description. Requires `If-Match`; missing is 428, stale is 409.                                                             |
| same                                     | DELETE  | `iam:write` | Requires the current ETag and disables rather than physically erases the binding; returns 204.                                                                    |

A binding exposes `binding_id`, issuer, principal type/id, tenant, environments, roles, active, description, created/updated timestamps and actors, integer revision, ETag, and schema version. ETags appear in the JSON body; response `ETag` headers are not consistently documented. POST currently behaves deterministically for an existing binding but the FastAPI handlers do **not** declare `Idempotency-Key`; the Console sends an operation-scoped key defensively and does not claim server idempotency. PATCH/DELETE likewise do not declare that header.

Canonical roles are `platform_admin`, `tenant_admin`, `operator`, `investigator`, `monitor_editor`, `workflow_approver`, `viewer`, and `collector`; canonical permissions are the `Permission` enum in `src/security/permissions.py`. No HTTP role/permission catalogue exists. The UI presentation catalogue labels identifiers only and never evaluates access.

Tenant/environment memberships exist only on `/auth/me`. The binding list is tenant-bounded but not environment-filtered. Service principals use principal type `service`; no directory lookup, secret generation, or lifecycle API exists. Platform-admin removal is rejected with 409 when it would remove the last active platform administrator. The browser never calculates or bypasses that invariant.

Security events are emitted to server persistence, but there is no bounded audit read route. There is no effective-access explanation route, system-version aggregate, identity directory, custom-role, custom-permission, bulk mutation, or principal search API.

## Gaps and UX response

- Inventory pagination/filtering/search/sort are absent. v1 labels the limitation and never claims the local role convenience filter is server-backed or complete.
- Role and permission catalogues have no API. The Console references version-controlled canonical backend identifiers; custom roles are unsupported.
- Audit reads and effective-access evaluation are unavailable. The audit page renders an honest unavailable state and never queries Elasticsearch.
- Idempotency is not an explicit OpenAPI IAM requirement; the client sends keys, while documentation avoids claiming durable replay guarantees.
- The runtime role-binding handlers use process state in `app.state`, despite a durable repository existing elsewhere. This is a Team 0 integration gap; Team 5 does not change it.
- ETag response headers are absent/inconsistent; the client captures headers and uses the response-body ETag.
- No API supplies certified status, API/build SHA, terminal migration, safe aggregate counts, recent changes, or service-principal counts. These remain unknown/unavailable.

## Boundaries, risk, and certification

Team 5 owns routes, presentation, safe mutation review, conflict/last-admin UX, preferences, accessibility, tests, evidence workflow, and documentation. Team 0 retains identity, RBAC meaning, enforcement, persistence, route policy, migrations, and certification. Primary risks are identifier disclosure, stale cross-context responses, privilege escalation, stale writes, destructive retries, telemetry leakage, and secret persistence. Controls include trusted selectors, abort signals, canonical options, ETags, explicit review, no automatic destructive retry, safe errors/request IDs, and versioned non-sensitive preferences. Hosted OIDC/Elasticsearch evidence and independent release certification remain CI/Team 0 gates, not local claims.
