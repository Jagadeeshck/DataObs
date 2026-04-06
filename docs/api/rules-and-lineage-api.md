# DataObs Rule and Lineage API

DataObs now includes a lightweight HTTP API for rule and lineage management.

## Run locally

```bash
python -m src.api.main
```

The server listens on `http://0.0.0.0:8080`.

## Endpoints

### Health
- `GET /health`

### Rule management
- `GET /rules` — list all rules
- `POST /rules/{rule_id}` — create/update rule
- `DELETE /rules/{rule_id}` — delete rule

Example payload:

```json
{
  "dataset": "prod.public.orders",
  "check": "freshness",
  "max_age_minutes": 60,
  "severity": "critical"
}
```

### Lineage management
- `GET /lineage/nodes` — list nodes
- `POST /lineage/nodes/{node_id}` — upsert a node
- `GET /lineage/edges` — list edges
- `POST /lineage/edges` — create edge (`source_node_id`, `target_node_id` required)
- `GET /lineage/impact/{node_id}?depth=5` — downstream impact traversal

## Production note
This API uses in-memory stores by default for portability. In production, wire these operations to Elasticsearch-backed repositories.
