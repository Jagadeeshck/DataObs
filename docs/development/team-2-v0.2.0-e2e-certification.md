# Team 2 v0.2.0 end-to-end certification matrix

**Team:** Team 2 — Data Quality, Jobs and Lineage  
**Branch:** `codex/v020-team2-e2e-certification`  
**Starting main:** `f62acd9f0d32ec827c26b7c8ccc56b18ac0c9401`  
**Target:** DataObs `v0.2.0`

This document is an evidence ledger, not a release authorization. A row is not promoted to release-ready until the final branch head has retained hosted evidence for every mandatory column.

## Previous exact-head baseline

The last merged Team 2 release-stabilization head was `6c8df8157e367644ae5c585dbe2a3f2efdc8e1be`.

| Capability | Previous hosted result | Disposition on this branch |
| --- | --- | --- |
| Data Reliability SLO | PASS — run 40671784439 | Re-run exact branch head; do not change formula unless a defect reproduces |
| Team 2 data-intelligence reconciliation | PASS — run 40671784297 | Re-run exact branch head |
| Job/Run backend / OpenLineage | PASS — run 40671784266 | Re-run exact branch head |
| Data Quality monitoring | Domain certify PASS; independent evidence verification FAIL due an intentionally skipped full-stack E2E test in the focused JUnit | Focus the workflow on executable Quality/security suites; full E2E proof belongs to CI integration stack |
| Data Quality Console | FAIL — legacy `/rules` crossed tenant boundaries | Fix Team 2 legacy rule scope and retain the existing security regression |
| Lineage Console | Backend/Console PASS; browser FAIL | Re-run after merged Team 5 browser fixes; shared browser failures remain Team 5-owned |
| Data Product hosted certification | FAIL — clean-install Data Product mapping ownership conflict | Preserve the released 0015 contract during first index creation; Team 0 review required |
| Data Product reconciliation | FAIL — same mapping family | Same correction and real ES 9.4.2 re-run |
| Full quality signal path | Not executed because shared CI prerequisites failed | Must execute with `RUN_INTEGRATION_TESTS=1`; retain `e2e-signal-path` |

## Corrections in this branch

### Legacy Quality rule tenant boundary

The legacy `/rules` handlers now bind reads, writes and deletes to the authenticated request tenant and environment. The memory store supports the same public rule ID independently across tenants/environments. Elasticsearch rule documents include environment, use an environment-scoped document ID, and fail closed if a caller attempts to use a store for another tenant.

This is a security/domain correction; it does not create a new Quality engine.

### Data Product mapping ownership

No released migration is modified.

On clean install, every concrete resource that migration `0015_data_product_360_productization` later validates is initially created with the same owning contract that 0015 declares:

- `dataobs-data-products-v1` → `DATA_PRODUCT_PROPERTIES`
- `dataobs-data-product-revisions-v1` → `DATA_PRODUCT_EVENT_PROPERTIES`
- `dataobs-data-product-operation-state-v1` → `DATA_PRODUCT_EVENT_PROPERTIES`
- 0015 membership/SLO/scorecard/coverage/impact/dependency resources → `DATA_PRODUCT_AUXILIARY_PROPERTIES`

Conflict detection remains fail-closed. Team 0 review is required because the correction is in the shared Elasticsearch registry.

### Focused Quality evidence

The focused Data Quality workflow no longer includes the environment-gated full signal-path test in its JUnit. That test is not removed or weakened: the authoritative production-representative execution remains the full CI integration stack.

The Quality Console backend workflow now runs only the executable Team 2 monitor and tenant/OIDC regression suites before browser validation.

### Manual run-now

Regression coverage now proves:

- deterministic execution ID for an explicit idempotency key;
- replay with the same key does not write duplicate work;
- tenant and environment are part of the execution identity;
- oversized idempotency keys fail before work is written.

The API remains asynchronous; queued is not completed.

## Exact-head evidence matrix

Populate final run/artifact IDs after hosted execution.

| Capability | Domain tests | Integration | ES 9.4.2 | PostgreSQL | Tenant/RBAC | Browser/a11y | Independent verification | Current state |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Monitor authoring/lifecycle | pending final head | n/a | pending | n/a | pending | pending | pending | functional_unvalidated |
| Monitor scheduling/lease/checkpoint | pending final head | pending where applicable | pending | n/a | pending | n/a | pending | functional_unvalidated |
| Missing/zero/stale Quality semantics | pending final head | pending | pending | pending | pending | pending | pending | functional_unvalidated |
| Manual run-now | regression added | n/a | pending indirect | n/a | scoped | pending | pending | functional_unvalidated |
| Quality signal path | unit/focused is not E2E proof | **mandatory CI integration stack** | mandatory | as compose requires | mandatory | Console investigation dependency | exact-SHA artifact required | blocked |
| OpenLineage ingestion/redaction | previous exact-head PASS | pending final-head rerun | pending | n/a | pending | Jobs journey pending | pending | functional_unvalidated |
| Job/Run projections | previous exact-head PASS | pending final-head rerun | pending | n/a | pending | pending | pending | functional_unvalidated |
| Dataset/column lineage | previous backend PASS | pending | pending | n/a | pending | pending | pending | functional_unvalidated |
| Cycle/truncation/partial evidence | previous backend PASS | pending | pending | n/a | pending | pending | pending | functional_unvalidated |
| Data Product membership | unit/contracts previously PASS | pending | pending after mapping correction | n/a | pending | dependency | pending | functional_unvalidated |
| Data Product reconciliation | unit/contracts previously PASS | pending | pending after mapping correction | n/a | pending | n/a | pending | functional_unvalidated |
| Data Reliability SLO | previous exact-head PASS | pending final-head rerun | workflow scope dependent | n/a | scoped evidence | n/a | pending | functional_unvalidated |
| Error budget/burn rate | previous exact-head PASS | pending final-head rerun | workflow scope dependent | n/a | scoped evidence | n/a | pending | functional_unvalidated |

## Required production-representative signal path

The mandatory end-to-end proof is:

```
Quality check
  -> OpenTelemetry
  -> Collector
  -> Elasticsearch
  -> Quality result
  -> Finding
  -> existing Team 3 deduplicated incident
  -> notification outcome
  -> API retrieval
  -> Console investigation
```

The canonical backend integration contract is `tests/integration/test_quality_signal_path.py` plus the OTel/API/alert integration tests run by the CI integration job. Fixture-only execution or a skipped integration marker is not certification.

The retained artifact must be `e2e-signal-path` for the exact final SHA and must contain successful JUnit plus redaction-safe scenario/correlation/deduplication evidence.

## Cross-team blockers and ownership

### Team 0

Current shared certification compose runs on the previous Team 2 head failed before live assertions because the API production image could not import `scripts.release.current_terminal_migration`:

`ModuleNotFoundError: No module named 'scripts'`

That is shared packaging/release infrastructure. Team 2 must not patch the Docker image or workflow infrastructure to hide it. Team 0 owns the production image correction and must review the Data Product registry change in this branch.

### Team 3

Team 3 owns incident correlation, deduplication, lifecycle and notification/automation behavior. Team 2 certifies that canonical Quality findings cross that existing boundary; it does not implement a second incident engine.

### Team 5

Team 5 owns the global Console/browser/accessibility harness. Team 2 owns Quality, Jobs and Lineage feature behavior. A shared shell or unrelated product journey failure is recorded as Team 5-owned; Team 2 does not weaken the browser suite.

## Release truth

Until the final branch head has executed and retained all mandatory hosted evidence, Team 2 remains **NO_GO / functional_unvalidated** for release certification.

No local test, workflow definition, fixture, or previous SHA is sufficient to promote the final branch head.
