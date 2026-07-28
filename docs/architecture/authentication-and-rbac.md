# Authentication and RBAC

DataObs is an OIDC resource server, not an identity provider. The API validates asymmetric signed access tokens against issuer-bound discovery/JWKS endpoints, constructs an immutable principal without retaining the token, maps only configured groups to built-in roles, and calculates permissions from one registry.

Every normal product request requires an explicit permission and trusted tenant context. Tenant and environment headers are selectors only: they can narrow validated identity access but never add membership. A single authorised context may be selected automatically; ambiguous access fails closed. Platform administrators remain subject to explicit tenant selection on product endpoints.

Built-in roles are `platform_admin`, `tenant_admin`, `operator`, `investigator`, `monitor_editor`, `workflow_approver`, `viewer`, and ingestion-only `collector`. Unknown token roles have no effect. Persisted bindings supplement external identity without creating a duplicate user directory.

The Console uses Authorization Code with PKCE and session storage through a standards-compliant OIDC client. It sends the access token to the API and treats `/api/v1/auth/me`, not decoded claims, as the effective-access authority.
