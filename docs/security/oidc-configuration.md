# OIDC configuration

Production requires `DATAOBS_AUTH_PROVIDER=oidc`, an HTTPS `DATAOBS_OIDC_ISSUER`, `DATAOBS_OIDC_AUDIENCE`, public Console `DATAOBS_OIDC_CLIENT_ID`, an explicit asymmetric `DATAOBS_OIDC_ALLOWED_ALGORITHMS`, and at least one `DATAOBS_OIDC_GROUP_ROLE_MAPPINGS` or `DATAOBS_OIDC_PLATFORM_ADMIN_GROUPS` mapping. Structured environment values use JSON; YAML uses native arrays/maps.

Configure client credentials for collectors at the external provider and map their group only to `collector`. Use short access-token lifetimes, provider-managed secret rotation, and overlap signing keys during JWKS rotation. Shared `API_TOKEN` authentication is rejected in production.

Development bypass is permitted only with `DATAOBS_ENV=development`, `DATAOBS_AUTH_PROVIDER=local`, and `DATAOBS_ALLOW_UNAUTHENTICATED_DEV=true`. Never use it in a shared environment.
