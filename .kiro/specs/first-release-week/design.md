# Design — DataObs v1.0.0 first release certification

## Architecture

```
Collection sources (OTLP / OpenLineage / Kafka / PostgreSQL Scanner)
    ↓
DataObs API + Workers (FastAPI, Python 3.11)
    ↓
Tenant/environment-scoped Elasticsearch 9.5.5 Enterprise indices (migrations 0001–0033)
    ↓
Quality / Stream / Job / Lineage / Data Product projections
    ↓
Incident correlation → redaction-safe notification outcomes (Slack / PagerDuty / ServiceNow)
    ↓
React DataObs Console (Elastic EUI 117, OIDC-authenticated)
```

Kibana and Elastic Enterprise features are authoritative analysis and storage components.
Never create parallel incident engines or separate product UIs.

## Release control plane

```
GitHub source commit (exact SHA)
    ↓ CI: mandatory Gate 0 jobs
Metadata / JUnit / evidence artifacts + digests
    ↓ Independent verification (same SHA, verified digest)
Gate 0 green → freeze candidate SHA
    ↓ Dispatch canonical Team 1–5 release workflows (workflow_dispatch)
Evidence artifacts (stream / quality / incidents / browser / security)
    ↓ Independent verifier accepts each
Protected platform + security + supply-chain certification
    ↓ Release authority GO
Immutable tag v1.0.0 → signed images → published support matrix
```

## Elastic Enterprise integration design

### ML anomaly detection (Layer B, post-v1.0.0)
- ML anomaly detector jobs created per active monitor per tenant
- ES ML runs detection natively; results polled and mapped to DataObs findings
- Monitor document stores `ml_job_id`; lifecycle-managed with monitor CRUD
- Migration `0034_ml_anomaly_detector_jobs` tracks job metadata

### Watcher alerting (Layer B, post-v1.0.0)
- Watcher watch registered when monitor activates, deregistered on deactivate/delete
- Watch fires → HTTP POST to DataObs internal endpoint → existing finding pipeline
- Watch ID stored on monitor document

### Transform summaries (Layer B, post-v1.0.0)
- Continuous transforms produce pre-computed asset health and quality summaries
- Powers Command Center tiles without expensive runtime aggregations
- Migration `0035_quality_transform_summaries` provisions summary index templates

### ESRE asset search (Layer B, post-v1.0.0)
- `semantic_text` field on asset documents for hybrid BM25 + vector search
- ELSER model deployed to ES; no external embedding service
- Migration `0036_asset_semantic_search` adds semantic_text mapping

## Version truth (all must match)
- DataObs application: `1.0.0`
- Helm chart: `version: 1.0.0`, `appVersion: "1.0.0"`
- Console package.json: `"version": "1.0.0"`
- FastAPI app: `version="1.0.0"`
- OpenAPI spec: `info.version: 1.0.0`
- Elasticsearch server: `9.5.5`
- Python client: `elasticsearch[async]==9.5.0`
- Terminal migration: `0033_team1_stream_schema_intelligence_runtime`

## Trust and data model

Every observation: tenant, environment, source, collection/evidence time, freshness,
status, confidence/coverage, correlation IDs, provenance.
Keep zero separate from no-data. Notification delivery records may be failed/unknown;
never assume success.

## Failure handling

- ES unavailable → expose `unavailable/error`; no fabricated healthy data
- Provider unknown → preserve unknown; checkpoint safety
- Artifact incomplete → release NO_GO
- Browser fixtures pass but live API fails → reject integrated acceptance
