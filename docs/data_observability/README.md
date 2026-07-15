# Data Observability with OpenLineage and Elasticsearch

DataObs accepts OpenLineage `RunEvent` payloads and projects them into Elasticsearch for operational data observability. OpenLineage is the event contract; Elasticsearch provides durable history, entity-centric views, search, correlation, alerting, and lineage traversal.

## Ingestion

OpenLineage clients can send events to the standard endpoint:

```bash
curl -X POST http://localhost:8080/api/v1/lineage \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  --data @examples/data_observability/openlineage_event.json
```

The legacy endpoint remains available at `POST /api/data-observability/lineage/events`.

DataObs validates `eventType`, `eventTime`, `run.runId`, `job.namespace`, `job.name`, and dataset `namespace`/`name`. Exact retries are idempotent because the raw event ID is derived from a canonical hash of the payload.

## Elasticsearch projections

- `dataobs-lineage-events-v1-<tenant>`: append-only data stream containing the original event, selected searchable fields, and flattened facets.
- `dataobs-jobs-v1-<tenant>`: current job metadata and first/last seen timestamps.
- `dataobs-job-runs-v1-<tenant>`: run lifecycle assembled from START/RUNNING/COMPLETE/FAIL/ABORT events.
- `dataobs-assets-v1-<tenant>`: dataset catalog projection.
- `dataobs-columns-v1-<tenant>`: schema-facet projection.
- `dataobs-lineage-edges-v1-<tenant>`: deterministic dataset dependency edges.
- `dataobs-column-lineage-edges-v1-<tenant>`: field-level dependencies and transformations.
- `dataobs-quality-runs-v1-<tenant>`: projected `dataQualityAssertions` results.

Unknown facets are retained using `flattened` mappings, while the full raw payload is stored with mapping disabled to avoid mapping explosion.

## Query APIs

```text
GET /api/v1/runs/{run_id}
GET /api/v1/jobs/{namespace}/{name}
GET /api/v1/datasets/{namespace}/{name}
GET /api/v1/lineage/{asset_id}/upstream?depth=5
GET /api/v1/lineage/{asset_id}/downstream?depth=5
GET /api/v1/lineage/{asset_id}/impact?depth=5
GET /api/v1/lineage/{asset_id}/columns/{column}/upstream
```

Traversal is cycle-safe and depth-bounded. Asset IDs use the readable `{namespace}:{name}` form, while jobs, events, columns, and edges also receive deterministic SHA-256 identifiers.

## Supported facets

The first implementation projects:

- dataset `schema`
- dataset `ownership`, `tags`, `documentation`, `version`, and `datasetType`
- input/output `dataQualityMetrics`
- dataset `dataQualityAssertions`
- output `columnLineage`
- run `nominalTime` and `errorMessage`

All other facets remain available in the raw event and flattened facet documents for future projectors.

## Local verification

```bash
pytest -q tests/test_data_observability.py tests/test_api_endpoints.py
```
