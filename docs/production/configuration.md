# DataObs Configuration

## Modes
Set `DATAOBS_ENV` to one of: `development`, `test`, `poc`, `production`.

## Source precedence
1. Environment variables (highest)
2. `DATAOBS_CONFIG` path if set
3. Default file (`config/dataobs.yaml`, or `config/dataobs_poc.yaml` in `poc` mode)
4. Built-in safe defaults (dev/test/poc only)

## Production requirements
In `DATAOBS_ENV=production`:
- `API_TOKEN` required.
- `DATAOBS_ALLOW_UNAUTHENTICATED_DEV` must be false (hard startup failure if true).
- `DATAOBS_STORE_BACKEND=memory` is rejected.
- `ELASTICSEARCH_URL` required.
- Elasticsearch auth required (`ELASTICSEARCH_API_KEY` or user/password).
- Rejects weak defaults like `changeme`, `dataobs_poc_elastic`, `dataobs_poc_kibana`.
- `DATAOBS_TENANT_ID` must be explicit (not `default`).
- TLS verification must remain enabled.

> **Security warning:** `DATAOBS_ALLOW_UNAUTHENTICATED_DEV=true` bypasses all authentication and must
> never be set in a shared, staging, or production environment. It is only permitted with
> `DATAOBS_ENV=development` and `DATAOBS_AUTH_PROVIDER=local`. The API will emit a prominent
> `WARNING` log line on startup when this flag is active.

## Legacy env vars kept
`API_TOKEN`, `API_HOST`, `API_PORT`, `ELASTICSEARCH_URL`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`, `DATAOBS_STORE_BACKEND`, `DATAOBS_TENANT_ID`, `LOG_LEVEL`.

## Docker / Kubernetes
Use the same environment variables in Docker Compose, Helm values, and Terraform-managed runtime env.
# OIDC and trusted tenancy

Production must set `DATAOBS_AUTH_PROVIDER=oidc`, `DATAOBS_OIDC_ISSUER`, `DATAOBS_OIDC_AUDIENCE`, `DATAOBS_OIDC_CLIENT_ID`, `DATAOBS_OIDC_ALLOWED_ALGORITHMS`, the configured group and tenant claims, and a trusted group-role/platform-admin mapping. Configure Console redirect and post-logout URIs at the provider and use an explicit CORS origin allowlist. Store provider client credentials for collector client-credentials grants in Kubernetes Secrets; the Console is a public PKCE client and has no client secret. The API needs outbound HTTPS/DNS access to issuer discovery and JWKS endpoints.

`API_TOKEN`, wildcard credentialed CORS, insecure issuers, unauthenticated mode, missing mappings, and symmetric/unsigned algorithms are forbidden in production. See [OIDC configuration](../security/oidc-configuration.md) and [tenant enforcement](../security/tenant-enforcement.md).
