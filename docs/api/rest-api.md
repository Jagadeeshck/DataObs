# DataObs REST API

## Auth
Use `Authorization: Bearer <token>` for protected endpoints.

## Request IDs
Send optional `X-Request-ID`; API echoes it, or generates UUID when missing.

## Error format
```json
{"error":{"code":"validation_error","message":"Validation error","details":{}},"request_id":"..."}
```
Covers 400/401/404/405/422/500.

## Pagination
Supported on `/rules`, `/quality/results`, `/lineage/nodes`, `/lineage/edges` with:
- `limit` (default 100, max 1000)
- `offset` (default 0)

Response includes:
- existing key (`rules/results/nodes/edges`)
- `count`
- `pagination` with `limit`, `offset`, `returned`, `total`, `has_more`.

## Filters
- `/quality/results`: `table,status,dataset,check_type,severity,run_id`
- `/rules`: `dataset,enabled,severity,check_type`
- `/lineage/nodes`: `node_type` (or `type`), `dataset`
- `/lineage/edges`: `source,target,relation` (or `relation_type`)

## curl examples
```bash
curl -H "Authorization: Bearer $TOKEN" -H "X-Request-ID: req-123" "http://localhost:8000/rules?limit=50&offset=0&dataset=orders"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/quality/results?table=orders&status=fail&limit=20"
```
