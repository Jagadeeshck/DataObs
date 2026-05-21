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
- `DATAOBS_ALLOW_UNAUTHENTICATED_DEV` must be false.
- `DATAOBS_STORE_BACKEND=memory` is rejected.
- `ELASTICSEARCH_URL` required.
- Elasticsearch auth required (`ELASTICSEARCH_API_KEY` or user/password).
- Rejects weak defaults like `changeme`, `dataobs_poc_elastic`, `dataobs_poc_kibana`.
- `DATAOBS_TENANT_ID` must be explicit (not `default`).
- TLS verification must remain enabled.

## Legacy env vars kept
`API_TOKEN`, `API_HOST`, `API_PORT`, `ELASTICSEARCH_URL`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`, `DATAOBS_STORE_BACKEND`, `DATAOBS_TENANT_ID`, `LOG_LEVEL`.

## Docker / Kubernetes
Use the same environment variables in Docker Compose, Helm values, and Terraform-managed runtime env.
