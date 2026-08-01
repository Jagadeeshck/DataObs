# Console authentication and secret handling

The Console preserves OIDC Authorization Code with PKCE. `/api/v1/auth/me` is authoritative for display identity, memberships and permission-sensitive discovery; unvalidated token decoding is not used. Callback redirects accept only same-origin relative paths, provider errors are withheld, and bearer values are never logged.

Frontend permission filtering is not authorization. Every API remains responsible for tenant membership and RBAC. Tenant headers can only be selected from the trusted context. The only local onboarding preference contains step and goal IDs. Tokens remain in session storage through `oidc-client-ts`; resolved provider secrets must never reach browser storage.
