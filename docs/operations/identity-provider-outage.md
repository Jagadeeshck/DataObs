# Identity-provider outage

Cached signing keys remain usable only for their configured TTL. Discovery/JWKS failures fail closed when no trusted key is available; they never enable local or shared-token fallback in production. Restore provider reachability, verify issuer/TLS/DNS, and allow controlled JWKS refresh. Emergency access must be an externally managed, audited break-glass OIDC identity. Do not change production to local authentication.
