# DataObs repository structure and feature-development guide

This guide explains where code belongs, which extension points are stable, and how to add new capabilities without coupling feature work to deployment or demo assets.

## Top-level layout

| Path | Purpose | Development guidance |
| --- | --- | --- |
| `src/api/` | Lightweight HTTP API for quality rules, quality results, lineage, and strategy endpoints. | Keep request parsing and response shaping here; put persistence concerns in store classes. |
| `src/quality/` | Quality engine, freshness, lineage, baselines, and pluggable checks. | New checks should live in `src/quality/checks/` and register through `registry.py`. |
| `src/alerting/` | Slack, PagerDuty, and ServiceNow delivery clients. | Keep clients small, injectable, and testable with fake HTTP transports. |
| `src/analytics/` | Detection and Elasticsearch ML helpers. | Put backend-specific analytics adapters here rather than in quality checks. |
| `src/core/` | Product model and enterprise blueprint logic. | Use this for pure domain logic that should not depend on Elasticsearch, HTTP, or Kubernetes. |
| `src/poc/` | Proof-of-concept pipeline and Elastic demo helpers. | Demo-only code belongs here so production modules stay reusable. |
| `integrations/` | External runtime examples such as Spark, dbt, Lambda, and Grafana Alloy. | Integration-specific dependencies and README files should stay under each integration folder. |
| `config/`, `k8s/`, `helm/`, `infra/` | Runtime configuration and deployment assets. | Keep environment defaults in `config/`; keep platform-specific rollout logic in its deployment folder. |
| `docs/` | Architecture, operations, production, API, and product documentation. | Update documentation in the same change as any public behavior or extension-point update. |
| `tests/` | Unit and integration tests. | Add fast unit tests next to the feature area; reserve `tests/integration/` for Docker/service-backed flows. |

## Quality-check extension point

Quality checks share a consistent result contract:

1. Implement `BaseCheck.run(...)` and return `CheckResult` with uppercase status values (`PASS`, `FAIL`, `WARN`, or `ERROR`).
2. Validate every configured SQL identifier with helpers from `src/quality/checks/sql.py` before interpolating it into a query.
3. Register the new type in `src/quality/checks/registry.py` so the engine and future APIs use one canonical check map.
4. Add unit coverage in `tests/test_quality_checks.py` for pass, failure, and validation paths.
5. Document required config keys in this guide or a feature-specific document before exposing the check in examples.

The registry/factory pattern keeps upcoming issue work small: a new check can be added without editing the scheduler loop, and backend-specific constructor needs can be isolated in one factory branch.

## Open-issue readiness review

The repository references existing GitHub issues for dynamic drift baselines, integration tests, Elasticsearch-backed stores, dbt telemetry, and anomaly detection. The current refactor prepares those areas by:

- Keeping built-in check registration centralized, making additional check types and issue-driven variants straightforward.
- Standardizing `DistributionDriftCheck` on the same `CheckResult` document shape used by other quality checks.
- Moving SQL identifier validation into reusable helpers so new checks inherit the same safety model.
- Separating production modules, proof-of-concept modules, integrations, and deployment assets in documentation so future features have obvious homes.

> Note: the public GitHub Issues API for `Jagadeeshck/DataObs` returned `404 Not Found` from this environment, so this review used issue references already present in the repository and README badges rather than live issue bodies.

## Development checks

Run the fast quality-check suite while iterating on new check behavior:

```bash
pytest tests/test_quality_checks.py -q
```

Run the full suite before opening a pull request when dependencies and external service assumptions are available:

```bash
pytest
```

## API store layer (FastAPI)

The API now uses one primary persistence contract (`StoreProtocol` in `src/api/store.py`) for both local memory mode and Elasticsearch mode.

### Backends

- `DATAOBS_STORE_BACKEND=memory` (default): uses `InMemoryStore`.
- `DATAOBS_STORE_BACKEND=elasticsearch`: uses `ElasticsearchStore`.

### Memory mode behavior

- In-process only; state resets on restart.
- Supports quality results, rule CRUD, lineage nodes, lineage edges, and downstream impact traversal (BFS).

### Elasticsearch mode behavior

- Stores quality results, rules, lineage nodes, and lineage edges in tenant-scoped indices.
- Reads and writes always include tenant guards to prevent cross-tenant reads.
- Lineage graph model stores both nodes (`doc_type=node`) and edges (`doc_type=edge`) in the lineage index for each tenant.

### Tenant isolation

- Tenant is resolved from `DATAOBS_TENANT_ID`.
- Queries include `tenant_id` filters and use tenant-specific index names:
  - `dataobs-quality-results-<tenant>`
  - `dataobs-rules-<tenant>`
  - `dataobs-lineage-<tenant>`

### Legacy compatibility notes

- `RuleStore` and `LineageStore` remain in `src/api/store.py` as compatibility adapters for legacy call sites and shared legacy indices.
- FastAPI route dependencies now use the unified store contract as the primary path.
