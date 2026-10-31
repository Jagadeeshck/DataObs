# Team 2 Sprint 4 — First-Release Data and E2E Certification

**Team:** Team 2 — Data Quality, Jobs and Lineage  
**Release:** v0.2.0  
**Branch:** `codex/sprint4-team2-e2e-proof`  
**Starting main:** `c3d3dfe63b2d8227612dc867988db268c8b7424f`

This document records executed evidence and exact-SHA certification state. A workflow definition, skipped test, fixture-only journey, or result from another SHA is not release proof.

## Starting exact-main evidence

| Capability | Run | Executed result on starting main | Sprint 4 disposition |
| --- | ---: | --- | --- |
| Data Quality Monitoring | 41120485805 | **PASS**, including independent evidence verification | Preserve unchanged; rerun final head |
| Job/Run backend | 41120485697 | **PASS**, including independent evidence verification | Preserve unchanged; rerun final head |
| Data Product hosted foundation | 41120485725 | ES 9.5.5, security and unit **PASS**; contracts failed only Black formatting | Format Team 2 migration regression; rerun final head |
| Data Product reconciliation | 41120485598 | ES 9.5.5, security and unit **PASS**; contracts failed only Black formatting | Format Team 2 migration regression; rerun final head |
| Data Quality Console | 41120485783 | backend/static/unit/build passed; shared global browser suite failed | Run Team 2 Quality browser/a11y journeys; hand global failures to Team 5 |
| Lineage Console | 41120485815 | backend/static/unit/build passed; shared global browser suite failed | Run Team 2 Jobs/Lineage browser/a11y journeys; hand global failures to Team 5 |
| Full CI | 41120485742 | integration-tests skipped after shared prerequisite failures | Dedicated Team 2 exact-SHA signal-path workflow required |

## Data Product certification state

The starting-main Data Product foundation and reconciliation workflows both reached and passed their real Elasticsearch 9.5.5 producer jobs. Security and unit producers also passed. Their only Team 2-owned blocker was Black rejecting `tests/integration/data_products/test_migrations_elasticsearch.py`.

The retained migration regression proves on a real test-owned Elasticsearch service:

- all released migrations apply;
- the released sequence remains contiguous through the current terminal migration;
- migration checksums match the immutable registry;
- repeat application is idempotent;
- `dataobs-reliability-status-v1.observed_value` is `double`;
- `dataobs-data-product-revisions-v1.revision` is `integer`;
- `dataobs-data-product-revisions-v1.operation_id` is `keyword`;
- `dataobs-data-product-operation-state-v1.revision` is `integer`;
- `dataobs-data-product-operation-state-v1.operation_id` is `keyword`;
- the 0017 → 0018 upgrade preserves legacy evidence even when a later additive field is safely pre-provisioned.

No released migration is modified and incompatible mapping checks remain fail-closed.

## Quality and Job/Run preservation

The focused Quality Monitoring and Job/Run backend workflows are intentionally unchanged. On the starting main SHA, both producer jobs and both independent verifier jobs passed. Sprint 4 requires the same workflows to remain green on the final PR head.

## Browser acceptance boundary

The starting-main Quality and Lineage workflows both passed their Team 2 backend, static, unit and production-build stages before failing in the shared global Playwright suite.

The failing browser cases include global shell/navigation, responsive overflow, Team 5 supportability, Streams/Pathways presentation and global accessibility assertions. Team 2 does not weaken or silently remove those release requirements: the Beta manifest separately requires Team 5's mandatory Console experience certification.

Sprint 4 scopes the Team 2 browser producers to the release journeys Team 2 owns:

**Quality**
- Quality inventory, authoring and monitor investigation;
- trusted tenant/environment cannot be overridden by URL input;
- expired/unauthorised identity fails closed before capability data loads.

**Jobs/Lineage**
- Jobs, Run 360 and lineage context from the trusted scope;
- trusted tenant/environment cannot be overridden by URL input;
- expired/unauthorised identity fails closed before capability data loads.

These journeys still execute Playwright and axe. Quality retains the supported Chromium/Firefox/WebKit matrix. Lineage retains its existing Chromium caller. Team 5 remains responsible for the separate global Console/browser/accessibility release gate.

## Full signal-path proof

The shared CI integration job is correctly defined to execute the production-representative path, but on starting main it was skipped because upstream shared jobs failed. Shared certification jobs also currently expose Elasticsearch on `127.0.0.1:19200` while an unscoped migration CLI invocation attempts `localhost:9200`; that belongs to Team 0's shared certification infrastructure.

Sprint 4 therefore adds `.github/workflows/team-2-sprint4-e2e-proof.yml`, using the existing canonical integration stack rather than a second runtime implementation.

The producer executes:

```
Quality check
  -> OpenTelemetry SDK
  -> OTLP Collector
  -> Elasticsearch
  -> persisted Quality result
  -> canonical Finding
  -> Team 3 incident correlation
  -> deduplicated Incident
  -> Slack / PagerDuty / ServiceNow delivery outcome
  -> authenticated API retrieval
```

It also executes the Data Product real-ES migration regression, captures migration status before and after repeated apply, and records the required mapping types.

The artifact is exactly `e2e-signal-path`.

The independent verifier requires:

- producer SHA equals the exact PR head;
- Elasticsearch is exactly 9.5.5;
- Data Product migration JUnit has tests, zero failures/errors and **zero skips**;
- signal-path JUnit has tests, zero failures/errors and **zero skips**;
- all five production-representative signal scenarios executed;
- OTel execution/trace correlation matches the signal summary;
- replay resolves to the same incident with zero notification replay;
- cross-tenant API reads remain denied;
- partial delivery records Slack failure and PagerDuty/ServiceNow success rather than false complete success;
- credentials are explicitly marked redaction-safe;
- migration status is unchanged after repeated apply;
- every applied migration has a retained checksum;
- the required reliability and Data Product mapping types match the writer contracts.

## Exact-SHA final matrix

Populate only from the final PR head.

| Capability | Workflow | ES 9.5.5 | Domain/security | Browser/a11y | Integration | Independent verifier | Final state |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Data Product foundation | Data Product hosted certification foundation | required | required | n/a | migration path | required | pending |
| Data Product reconciliation | Data Product reconciliation certification | required | required | n/a | reconciliation path | required | pending |
| Data Quality Monitoring | data-quality-monitoring | required | required | n/a | focused provider | required | pending |
| Job/Run backend | job-run-backend | required | required | n/a | OpenLineage/adapters | required | pending |
| Data Quality Console | data-quality-console-v1 | required | required | required | n/a | required | pending |
| Lineage Console | lineage-analysis-console | required | required | required | n/a | required | pending |
| Quality → incident E2E | Team 2 — Sprint 4 First-Release E2E Proof | required | required | Console dependency only | **required, skip-free** | **required** | pending |
| Shared global Console | Team 5 Console release gate | Team 5 contract | Team 5 contract | **required** | n/a | Team 5 contract | external Team 5 handoff |
| Shared full release CI | CI / Team 0 certification | Team 0 contract | Team 0 contract | Team 0/5 contract | shared path | Team 0 contract | external Team 0 handoff |

## Release truth

Team 2 remains **NO_GO** until the final Sprint 4 PR head has successful, retained, independently verified evidence for every Team 2 mandatory row above. The dedicated Team 2 E2E proof does not authorize the overall product release and does not replace Team 0 or Team 5 mandatory gates.
