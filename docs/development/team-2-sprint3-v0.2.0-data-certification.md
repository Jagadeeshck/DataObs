# Team 2 Sprint 3 — v0.2.0 Data Certification

**Team:** Team 2 — Data Quality, Jobs, Lineage and Data Products  
**Release:** v0.2.0  
**Branch:** `codex/sprint3-team2-data-certification`  
**Base main:** `855345eb02250f9a738abe44bd520247243032bf`  
**Base includes:** Team 2 PR #322, Team 5 PR #321 and Team 0 PR #323.

This document records release evidence only. A workflow definition, local test, skipped integration test, or result from a different SHA is not certification for this branch.

## Mission

Complete Data Product migration and data-observability certification while preserving the already passing Data Quality Monitoring and Job/Run backend.

## Previous hosted evidence

The following runs executed on `8115f557ad7f6c53ab73054dc356f7bbfb676054`.

| Capability | Run | Result | Independent verification |
| --- | ---: | --- | --- |
| Data Quality Monitoring | 40869887974 | PASS | PASS — job 123447001867 |
| Job/Run backend | 40869887991 | PASS | PASS — job 123446679372 |
| Data Product hosted foundation | 40869888209 | FAIL | not produced |
| Data Product reconciliation | 40869887921 | FAIL | not produced |
| Data Quality Console | 40869888220 | FAIL | FAIL because browser evidence was never reached |
| Lineage Console | 40869888163 | FAIL | FAIL because browser evidence was never reached |

The Quality Monitoring and Job/Run workflows are preserved unchanged by this Sprint 3 branch.

## Failure analysis

### Data Product hosted foundation and reconciliation

The Data Product unit and contract jobs passed. The real Elasticsearch jobs failed while applying the full released migration chain.

The concrete hosted error was:

`Incompatible existing mapping on dataobs-reliability-status-v1: observed_value`

This was not a Data Product 0015 mapping failure. The Data Product certification traverses the shared migration chain, where the global mapping union had created `observed_value` before the first released reliability mapping owner could validate it.

Team 0 PR #323 is now merged in the branch base. It preserves the first released explicit field definition for every index during clean creation and adds a regression that specifically requires:

`dataobs-reliability-status-v1.observed_value -> double`

Team 2 does not duplicate or weaken that shared registry correction.

This branch adds a real-Elasticsearch Data Product migration regression proving the Team 0 correction on the actual hosted clean-install path and also re-proves the Data Product revisions and operation-state writer contracts.

### Data Quality Console

The Quality monitor/lifecycle/tenant/security backend step passed. The failure occurred in Console static checks at `pnpm format:check`.

The only reported files were:

- `ui/dataobs-console/e2e/console.spec.ts`
- `ui/dataobs-console/e2e/fixtures/release.ts`
- `ui/dataobs-console/e2e/release-critical-journeys.spec.ts`

Those are shared Team 5 release-browser files. Team 5 PR #321 is merged in the branch base and explicitly formatted/stabilised those certification specs. Team 2 does not alter the shared browser harness.

### Lineage Console

The lineage traversal/cycle/truncation/correlation/tenant backend step passed. The Console failed at the same shared Team 5 Prettier check and therefore never reached Playwright. Its independent verifier correctly failed because `results/browser.xml` was absent.

The Sprint 3 rerun must distinguish a backend failure from a shared browser failure and must not fabricate browser evidence.

## Hosted Data Product regression

`tests/integration/data_products/test_migrations_elasticsearch.py` now requires the real Elasticsearch 9.4.2 clean-install path to prove:

- full released migration application succeeds;
- migration checksums remain unchanged;
- `dataobs-reliability-status-v1.observed_value` is `double`;
- `dataobs-data-product-revisions-v1.revision` is `integer`;
- `dataobs-data-product-revisions-v1.operation_id` is `keyword`;
- Data Product operation-state `revision` is `integer`;
- Data Product operation-state `operation_id` is `keyword`;
- repeat migration application is idempotent.

No released migration is modified and incompatible mapping checks remain fail-closed.

## Data Product domain correctness

Existing certification remains authoritative for:

- reviewed membership and dependency projections;
- reconciliation operation state and replay;
- OCC fencing and stale-worker rejection;
- tenant isolation;
- environment isolation;
- same operation ID across independent scopes;
- wrong-scope plan/result/history/search denial;
- wrong-scope claim denial without consuming the valid OCC token;
- reliability score/evidence contracts.

The hosted Elasticsearch and security jobs must execute after migration apply; skipped downstream tests caused by a failed migration do not count.

## Exact-SHA certification matrix

Populate this matrix only from the final PR head.

| Capability | Workflow | Domain | ES 9.4.2 | Tenant/security | Browser/a11y | Independent verifier | Evidence artifact | Final state |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Data Quality Monitoring | data-quality-monitoring | prior PASS; rerun required | required | required | n/a | required | data-quality-monitoring-v1-evidence | pending |
| Job/Run + OpenLineage backend | job-run-backend | prior PASS; rerun required | required | required | n/a | required | job-run-backend-evidence | pending |
| Data Product hosted foundation | Data Product hosted certification foundation | required | **required** | required | n/a | required | foundation evidence | pending |
| Data Product reconciliation | Data Product reconciliation certification | required | **required** | **required** | n/a | required | reconciliation evidence | pending |
| Data Quality Console | data-quality-console-v1 | required | required | required | **required** | required | data-quality-console-v1-evidence | pending |
| Lineage Console | lineage-analysis-console | required | required | required | **required** | required | lineage-analysis-console-evidence | pending |
| Quality → incident signal path | CI integration-tests | required | **required** | **required** | Console investigation dependency | retained exact-SHA proof | e2e-signal-path | pending |

## Cross-team boundaries

### Team 0

Team 0 owns the shared Elasticsearch migration registry and the first-released mapping-owner correction merged in PR #323. Team 2 consumes and certifies that correction; any further shared registry change requires Team 0 review.

### Team 3

Team 3 owns finding-to-incident correlation, incident deduplication, lifecycle and notification/automation behavior. Team 2 certifies that the canonical Quality finding crosses that boundary. No second incident engine is permitted.

### Team 5

Team 5 owns the shared Console shell, browser matrix and accessibility harness. Team 2 owns Quality and Lineage feature correctness. Browser failures must be attributed by actual failing step; the browser suite must not be weakened to obtain a green result.

## Release rule

Team 2 remains **NO_GO** for v0.2.0 data certification until the exact final SHA has:

1. real Elasticsearch 9.4.2 Data Product migration evidence;
2. executed Data Product security/isolation evidence;
3. Quality and Lineage browser/accessibility evidence;
4. independently verified Quality and Job/Run evidence;
5. a non-skipped production-representative end-to-end signal-path artifact.
