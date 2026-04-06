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

### Enterprise strategy planning
- `GET /strategy/enterprise-backlog?implemented=<csv_keys>` — returns a prioritized backlog of capabilities that improve enterprise contract conversion.

Example:

```bash
curl "http://localhost:8080/strategy/enterprise-backlog?implemented=freshness,monitor_bootstrap"
```

This endpoint helps presales and delivery teams quickly decide which platform investments should be implemented next to improve credibility with enterprise buyers.

## Production note
This API uses in-memory stores by default for portability. In production, wire these operations to Elasticsearch-backed repositories.
