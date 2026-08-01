# Service principals
Service tokens use validated `azp` or `client_id` in the configured allowlist, optionally require `jti`, and require an active durable `service` binding. They do not inherit browser group roles. Give collectors only `collector`; rotate credentials at the OIDC provider and disable the binding during response. Shared static production API tokens are forbidden.
