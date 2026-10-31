# Team 1 Sprint 3 v0.2.0 certification closure

## Scope

Branch: `codex/sprint3-team1-streams`

Audited latest main at branch creation:

`855345eb02250f9a738abe44bd520247243032bf`

No product feature is added. This change only closes Team 1 release-certification plumbing and evidence-scope defects.

## Prior failed-run diagnosis

| Capability | Run | First meaningful failure | Disposition |
| --- | --- | --- | --- |
| Stream Observer | [40869888223](https://github.com/Jagadeeshck/DataObs/actions/runs/40869888223) | Producer passed, independent verifier rejected the artifact because mandatory security/tenant evidence contained skipped tests | Team 1 evidence-scope defect. The two skips are Team 2 Data Product reconciliation security tests that require their own certification profile. |
| Kafka Cluster 360 | [40869888219](https://github.com/Jagadeeshck/DataObs/actions/runs/40869888219) | Shared mapping conflict on `dataobs-reliability-status-v1.observed_value`; reusable backend also stopped at Black on shared files | The mapping conflict and shared formatting drift were subsequently repaired by merged Team 0/Team 2/Team 5 work. |
| Connector / Schema 360 | [40869888299](https://github.com/Jagadeeshck/DataObs/actions/runs/40869888299) | Same shared reliability-status mapping conflict; reusable validation stopped on shared formatting | Shared dependency, now revalidated against latest main. |
| Stream 360 Core | [40869888056](https://github.com/Jagadeeshck/DataObs/actions/runs/40869888056) | Same shared reliability-status mapping conflict | Shared dependency. |
| Pathway Intelligence | [40869888044](https://github.com/Jagadeeshck/DataObs/actions/runs/40869888044) | Same shared reliability-status mapping conflict | Shared dependency. |
| Pathway Explorer | [40869888088](https://github.com/Jagadeeshck/DataObs/actions/runs/40869888088) | Same shared reliability-status mapping conflict | Shared dependency on that candidate. |

## Stream Observer artifact diagnosis

Run 40869888223:

- producer SHA: `8115f557ad7f6c53ab73054dc356f7bbfb676054`
- run attempt: `1`
- artifact: `stream-observer-backend-v1-evidence`
- artifact ID: `12896529345`
- artifact download layout: named artifact is extracted directly into `downloaded-evidence`
- producer job: success
- verifier job: failure

The producer generated root-level `metadata.json` and `evidence.json` plus result XML under `results/`. The verifier correctly found the artifact and validated repository/workflow/run/SHA/version metadata.

The failure was not layout, SHA or run-ID mismatch. It was:

`ERROR: security, tenant, browser, or accessibility tests were skipped`

Producer JUnit summary:

- 233 passed
- 2 skipped
- Kafka real-stack: 1 passed

The skipped tests were:

- `tests/security/data_products/test_reconciliation_security.py`
- `tests/security/data_products/test_reconciliation_sentinels.py`

Those tests belong to the Team 2 Data Product runtime-foundation profile and intentionally skip unless `RUN_INTEGRATION_TESTS=1`, `DATA_PRODUCT_CERTIFICATION_PROFILE=data-product-runtime-foundation`, and a Data Product evidence directory are supplied.

Team 1 does not set another team's certification profile. Instead the Team 1 workflows now exclude `tests/security/data_products` while retaining the rest of the shared security/tenant suite.

Generate and verify still require exactly the same mandatory suites:

- elasticsearch
- kafka
- observer
- security
- tenant

The verifier's fail-closed skip rule is unchanged.

The current shared verifier records `workflow_run_attempt` in `evidence.json`; its independent verify path validates SHA, repository, workflow, run ID, Elasticsearch version, terminal migration, suite declaration and JUnit contents. Attempt-level validation is a Team 0 verifier concern and is not changed here. Run 40869888223 was attempt 1, so this did not cause that failure.

## Shared migration revalidation

The prior `dataobs-reliability-status-v1.observed_value` failure belonged to shared mutable-index bootstrap mapping ownership.

Merged Team 0 PR #323 now derives the earliest released explicit field owner for mutable indices before generic shared fields can pre-empt the owner type.

Fresh main Pathway Intelligence run:

[40961601097](https://github.com/Jagadeeshck/DataObs/actions/runs/40961601097)

Result: **PASS**.

This proves the released migration chain now reaches and executes the Pathway Intelligence fixture workflow on the current integrated main. Team 1 adds no migration and changes no released checksum.

## Fresh Pathway Explorer failure

Fresh main run:

[40961601227](https://github.com/Jagadeeshck/DataObs/actions/runs/40961601227)

The released migration chain completed through terminal migration `0033_team1_stream_schema_intelligence_runtime`.

The first failure after migration was:

`ModuleNotFoundError: No module named 'packages'`

from direct execution:

`python scripts/seed_console_demo.py`

The capability caller now uses:

`python -m scripts.seed_console_demo`

so repository root imports resolve without modifying the shared seeder.

## Security evidence boundary

Team 1 release workflows must not count Team 2 Data Product security tests as skipped mandatory Team 1 evidence.

Release-critical Team 1 callers now explicitly exclude only:

`tests/security/data_products`

They continue to execute the rest of `tests/security`, including tenant/RBAC/Gate 0 security contracts relevant to Team 1 API usage.

No security assertion is xfailed, disabled or weakened.

## Semantics retained

The merged Team 1 implementation still preserves:

- measured zero != missing;
- stale != current;
- unknown != zero;
- missing lag != zero lag;
- partial evidence != complete evidence;
- pressure != saturation;
- backlog growth != provider saturation;
- bottleneck candidate != root cause;
- dependency != impact.

Kafka offsets, lease expiry, checkpoints, pathway watermark/replay, bounded traversal, tenant/environment isolation and reliability append/OCC/signal/checkpoint ordering remain covered by the merged Team 1 regression suites.

## Exact-SHA acceptance matrix

This matrix must be updated with the new PR-head workflow URLs before the PR is promoted.

| Capability | Unit/domain | ES 9.5.5 | Kafka real stack | Tenant isolation | Browser/API | Independent evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stream Observer | pending PR head | pending | pending | pending | API pending | pending | BLOCKED |
| Kafka Cluster 360 | pending PR head | pending | NOT_APPLICABLE | pending | pending | pending | BLOCKED |
| Connector / Schema 360 | pending PR head | pending | NOT_APPLICABLE | pending | pending | pending | BLOCKED |
| Stream 360 Core | pending PR head | pending | covered by observer where applicable | pending | pending | pending | BLOCKED |
| Pathway Intelligence | current main PASS; PR head pending | current main PASS | NOT_APPLICABLE | pending | API pending | pending | BLOCKED |
| Pathway Explorer | pending after seeder fix | current main migration PASS | NOT_APPLICABLE | pending | pending | pending | BLOCKED |
| Stream / Pathway Reliability | pending PR head | pending | NOT_APPLICABLE | pending | pending | pending | BLOCKED |

No row becomes PASS until exact-head hosted evidence exists for the required dimensions.
