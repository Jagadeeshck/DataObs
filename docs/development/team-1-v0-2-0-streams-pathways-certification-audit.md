# Team 1 v0.2.0 Streams and Pathways certification audit

## Decision: BLOCKED

This is release closure for [draft PR #309](https://github.com/Jagadeeshck/DataObs/pull/309), branch `codex/release-team1-streams`. No new provider, product feature, remediation, released migration, shared security configuration, reusable workflow or Console shell was added or changed.

The domain/source corrections are committed as `d784d0103d09f0a7d17b446ee5f77a454325fb98`; the additional owned workflow bootstrap corrections are `b71ca6de20ff4af4b842ab19bcf95432a3398810`. Local checks exercise that source; they are not hosted certification. The audit-only commit containing this document is a separate candidate SHA. Its exact-head workflow URLs and current outcomes are recorded in the PR description/checks, not inferred from earlier runs.

Revalidated main: `09fa1fe615c69f79a8056772a4b424b5c564fb86`. Inspected prior PR head: `62f907da40d8c32961bcbcdb5859f96b5b31ae6e`. [Team 2 #310](https://github.com/Jagadeeshck/DataObs/pull/310), head `48fb74db015abc62978c2edacc5f21f94a25faa4`, and [Team 0 #311](https://github.com/Jagadeeshck/DataObs/pull/311), inspected head `60642df8027bd78c1a30ced44e3b077f2b78aab7`, remain open. Their shared registry repair is not in main. No speculative rebase or duplicate registry repair was performed.

## Latest hosted triage inspected before source edits

All runs below have `head_sha=62f907da40d8c32961bcbcdb5859f96b5b31ae6e`. These are previous-candidate results, not proof for the corrected source or final PR head.

| Workflow | Run / rerun reference | Job; first failed step | Exact error / assertion | Owner; root cause and disposition | Result |
| --- | --- | --- | --- | --- | --- |
| `pathway-intelligence-backend.yml` | [40654238411](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238411) | `verify`; Apply released migrations | `RuntimeError: Incompatible existing mapping on dataobs-data-products-v1: description, owner, revision, tags` | Team 0/2: shared clean-install mapping ownership; await approved #310/#311 repair | BLOCKED |
| `stream-observer-backend.yml` | [40654238894](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238894) | `certify`; Observer projections, intelligence, HTTP boundaries, leases and isolation | `tests/stream_360/test_stream_capacity_runtime.py:94: AttributeError: 'CapacityBottleneck' object has no attribute 'dimension'`; 1 failed, 147 passed, 2 skipped | Team 1: regression referenced nonexistent field; corrected to the real `candidate` contract while retaining saturation/confidence assertions | FAIL |
| `cluster-360-console.yml` | [40654238755](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238755) | `verify`; Apply migrations and seed deterministic projections | Same exact Data Product mapping error above | Team 0/2 dependency; reusable backend also failed owned import ordering, now corrected. Reusable Console passed; that does not make the whole capability pass | BLOCKED |
| `connector-schema-360-console.yml` | [40654238667](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238667) | `exact-commit-evidence`; Migration immutability and Elasticsearch seed/persistence/API isolation | Same exact Data Product mapping error | Team 0/2 dependency; `backend / validate` also failed owned Ruff import ordering. `console / validate` failed the full Playwright step; no broad browser PASS is claimed | BLOCKED |
| `stream-360-core-console.yml` | [40654239039](https://github.com/Jagadeeshck/DataObs/actions/runs/40654239039) | `verify`; Apply migrations and seed deterministic stream projections | Same exact Data Product mapping error | Team 0/2 dependency; domain assertions were not reached | BLOCKED |
| `pathway-explorer-console.yml` | [40654238267](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238267) | `exact-commit-evidence`; Boundaries, migrations, seed, and backend tests | Same exact Data Product mapping error | Team 0/2 dependency; retain Team 5 full browser/accessibility dependency | BLOCKED |
| `stream-pathway-reliability-runtime-v1.yml` | [40654238795](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238795) | `exact-commit-evidence`; Elasticsearch migration and deterministic runtime tests | Same exact Data Product mapping error | Team 0/2 dependency; no bypass or released checksum edit | BLOCKED |
| `team-1-stream-capacity-planning-experience-v1.yml` | [40654238897](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238897) | `capacity-planning`; focused pytest step | Same nonexistent `CapacityBottleneck.dimension` assertion | Team 1: corrected concrete assertion; 8 other tests had passed | FAIL |

The complete prior-head failed-job inventory, including existing runtime workflows, is retained in [prior-head-workflow-failures.json](../../evidence/team-1-v0-2-0-local/prior-head-workflow-failures.json). Each record includes workflow/run/head, job URL, first failed step, exact error, owner and disposition. Additional owned plumbing defects confirmed from those logs were corrected: missing pnpm version in multi-broker/anomaly Console jobs, missing runtime dependencies (`ModuleNotFoundError: No module named 'elasticsearch'`) in schema runtime/reconciliation callers, and a fresh-install doctor invoked before apply (`ready: false`, exit 2). Caller fixes pin pnpm 10.28.1/Node 24.15.0, install canonical runtime plus CI requirements, apply before requiring ready, and install Chromium for direct Console callers. Full migration failure remains fatal; shared gates are not relaxed. Broad global lint/type/browser failures remain separately owned dependencies.

The observer independent verifier on run 40654238894 rejected unsuccessful JUnit. Fixing the producer does not authorize declaring its artifact valid: the shared verifier also rejects *any* skipped test when security/tenant suites are declared (`scripts/certification/verify_product_evidence.py`). The normal selected security suite has two separately opted-in Elasticsearch security tests. Team 0 must resolve mandatory-versus-optional evidence classification without relaxing required assertions. Team 1 did not edit the shared verifier or disable either security test.

Prior-head diagnostic artifact [12802219799](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238894/artifacts/12802219799) contains the failed observer producer; it is not accepted certification.

Earlier producer [40652669752](https://github.com/Jagadeeshck/DataObs/actions/runs/40652669752), artifact [12799504917](https://github.com/Jagadeeshck/DataObs/actions/runs/40652669752/artifacts/12799504917), is retained historical evidence only. It does not certify this candidate. PR #309's corrected single-artifact extraction root (`downloaded-evidence`), canonical migration callers, dynamic reliability terminal metadata, concrete typing and mixed-signal fix remain intact.

## Team 1 defects closed

- Kafka commit reads now explicitly select the observed group through `AdminClient.list_consumer_group_offsets`; the observer's watermark reader no longer supplies its own group's commits. Inactive groups with persisted commits remain observable.
- Offset truth-table regressions cover measured zero, committed offset zero, missing high watermark, missing commit, missing partitions, invalid negative offsets, stale samples and inconsistent observation windows. Inconsistent windows produce unknown lag with `inconsistent_offset_window`, rather than a fabricated healthy zero.
- Group totals, maximum partition lag and topic rollups require complete measured partition evidence. Offset projection writes now precede successful offset checkpoint advancement. Missing group inventory differs from an observed empty group set.
- Kafka inventory processing has explicit caps of 1,000 topics, 1,000 groups and 10,000 partition inventory rows. Offset collection has a hard 100,000-combination limit; truncation and source failures remain explicit. Kafka metadata/list APIs return a broker-side list; these limits bound client processing/output, not the broker's metadata response size.
- Cluster 360 no longer turns absent partition-health fields into zero failed partitions. It retains observed critical failures even when other evidence is incomplete. Missing connector evidence remains unknown; stale status retains priority.
- Pathway body selectors and conflicting query/header environment selectors cannot override authenticated scope. Pathway reads use allowlisted aliases, bounded pages/evidence terms, literal match queries and deterministic `_id` tie-breaks; `orders*?` remains text.
- Pathway overlap scans retain a continuation after a full page. Late replay cannot regress the event watermark. Source patterns are restricted to the documented APM/Kafka families, with page/document caps. Tests simulate failure after projection but before checkpoint, restart, duplicate replay, scan continuation and canonical identity convergence.
- Graph selection is stable across input order before truncation, and traversal stops when its output bound is reached. Unknown/stale edges cannot establish healthy pathway status; missing latency remains unknown, zero remains zero, and bottleneck/change wording stays non-causal.
- Reliability recovery reconciles the immutable appended evaluation after projection/signal failure, preserving its original transition rather than recomputing from the partially updated current projection. Repeated projection of the same evaluation is idempotent. Append → OCC projection → signal → checkpoint → runtime health ordering is tested.
- Reliability, Stream Intelligence and Schema Intelligence reject expired lease tokens even before a successor takes ownership. Pathway renewal also rejects an expired lease.
- Connector task metadata and schema summaries/references have nested allowlists. Schema runtime rejects nested bodies/payloads/credentials, constrains indices and source fields, and uses bounded scoped reads. A configured compatibility mode is not represented as a successful compatibility evaluation.
- Stream domain component tests cover zero, unknown, stale, partial, unavailable and not-configured states. Pathway missing values render `Unknown`; shared shell, styles and axe assertions were not changed.
- The owned observer workflow executes the real Kafka regression and retains its actual JSON result. Synthetic `lag_messages:90`, retention/replication health and static lease/isolation PASS declarations were removed. Canonical JUnit remains the evidence for unit assertions. Integration opt-in is scoped to the Kafka-only invocation, so it does not silently enable unrelated Elasticsearch security fixtures.

## Local validation

- Focused domain/security/paging suite: **227 passed, 2 skipped**. The two skips are `tests/security/data_products/test_reconciliation_security.py` and `test_reconciliation_sentinels.py`, both requiring their real Elasticsearch security fixture; neither is counted as passed.
- Kafka integration: **1 passed**, separately executed against `apache/kafka:3.9.1`, image digest `sha256:4ceccc577f03f51f6af8dbfda55194d0d892f4fa7913ffbded567ce3895622ed`. One broker, three partitions, 60 deterministic messages, commits `[0,5,30]`, high watermarks `[10,20,30]`, lag `[10,15,0]`, total 25, maximum 15. After real consumer catch-up: total/maximum zero. Closing/reopening the observer produces identical offsets and lag. This is not three-broker certification or durable Elasticsearch checkpoint evidence.
- Console: **146 passed across 24 files**; typecheck, production build, bundle budget and changed-domain ESLint/Prettier passed. Build retains an existing large-chunk warning. No local full Playwright/axe certification is claimed.
- Owned Python scope: Ruff, Black, Mypy (**73 source files**) and compileall passed. Workflow YAML and embedded shell syntax passed. Team boundary checks passed; **33 released migrations unchanged**.
- Broader final-source Python run: **1,440 passed, 2 failed, 28 skipped**. Diagnostic results are retained separately. The known shared failures are generated capability documentation drift (Team 0 #311) and `tests/test_api_v1_foundation.py` selecting tenant `t1` with the default local identity (403 `tenant_access_denied`, expected 201; Team 2 fixture). Regenerated shared documentation was restored; no unrelated fix or xfail was added.

Machine-local JUnit, logs and measured Kafka JSON are under `/workspace/team1-release-evidence/`. They are local development evidence, not GitHub artifact URLs or publication evidence. The committed compact local bundle under `evidence/team-1-v0-2-0-local/` explicitly records its source SHA and local scope.

## Supported acceptance matrix

PASS here denotes the particular tested dimension only. BLOCKED in the final status means no release certification exists. NOT_APPLICABLE denotes a dimension that does not apply, not an unexecuted required check. Console contract cells refer to focused domain/component checks, not full browser certification.

| Capability | Implementation | Unit tests | ES 9.4.2 | Kafka real-stack | Tenant isolation | Console contract | Hosted exact-SHA | Status | Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kafka cluster/topic inventory | PASS | PASS | BLOCKED | PASS | PASS | PASS | BLOCKED | BLOCKED | Shared migrations/projection mappings; hosted proof |
| Consumer groups and lag | PASS | PASS | BLOCKED | PASS | PASS | PASS | BLOCKED | BLOCKED | Shared mappings; durable projection/checkpoint proof |
| Zero/missing/stale/unknown | PASS | PASS | BLOCKED | PASS | PASS | PASS | BLOCKED | BLOCKED | Mandatory exact-head evidence |
| Bounded stream queries | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | PASS | BLOCKED | BLOCKED | Live Elasticsearch query contract |
| Pathway deterministic topology | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | PASS | BLOCKED | BLOCKED | Shared migration gate |
| Pathway health/latency/bottleneck | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | PASS | BLOCKED | BLOCKED | Shared migration and browser gates |
| Pathway replay/late arrival/checkpoint | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | NOT_APPLICABLE | BLOCKED | BLOCKED | Live durable restart/fencing evidence |
| Stream/pathway reliability | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | PASS | BLOCKED | BLOCKED | Live append/OCC/signal/checkpoint proof |
| Lease expiry/restart recovery | PASS | PASS | BLOCKED | PASS | PASS | NOT_APPLICABLE | BLOCKED | BLOCKED | Durable Elasticsearch takeover/OCC evidence |
| Connector metadata/privacy | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | PASS | BLOCKED | BLOCKED | Real Connect and full browser/hosted proof |
| Schema metadata/privacy/impact | PASS | PASS | BLOCKED | NOT_APPLICABLE | PASS | PASS | BLOCKED | BLOCKED | Real Registry and full browser/hosted proof |

## Team 0 / Team 2 / Team 5 dependencies

### Shared clean-install gate — Team 0/2

Merge the approved shared fix from #310/#311 before rebasing this PR. Then run clean Elasticsearch **9.4.2**, the full released chain and a second idempotent apply, followed by all Team 1 integration/API persistence gates. No released migration edits, checksum changes, index deletion or migration bypass is permitted. Until that occurs, Elasticsearch capability rows remain BLOCKED.

### Projection mapping handoff — Team 0 with Team 1

A static comparison against the current shared `_mapping(index)` builder reveals pre-existing producer/schema drift. Example emitted fields absent from its strict contract:

- `dataobs-kafka-clusters-v1`: `broker_count`, `consumer_group_count`, `controller_id`, `health`, `source_coverage`, `topic_count`.
- `dataobs-kafka-consumer-groups-v1`: `assignments`, `coordinator`, `group_id`, `members`, `protocol`.
- Existing Console lag contract additionally needs `total_lag`, `maximum_lag`, bounded `lag_heatmap` and `data_status`; these are also absent from the shared Kafka mapping properties.

This is a source-contract comparison, not an observed clean-install mapping after #310/#311. Once that gate is repaired, compare the final installed mappings with the producers and approved Console manifest. Team 0 must approve any necessary additive forward migration; Team 1 did not mutate registry mechanics or released definitions. Field shapes must preserve numbers as numbers, arrays/objects as appropriate and null as unknown. The owned writer fails normally if Elasticsearch rejects a projection and does not advance its successful checkpoint.

For missing fields, a compatible additive mapping is the expected repair; it does not establish a reindex requirement. If an actual incompatible existing type is found, retain the old mapping and evidence, prepare a new versioned destination, reindex and verify counts/isolation, atomically switch aliases, and retain the old index for reviewed rollback. No such cutover is authorized or implemented here.

### Historical `dataobs-findings-v1` concern — NOT REPRODUCED

Authoritative source comparison: current `_mapping('dataobs-findings-v1')` and `INCIDENT_AUTOMATION_PROPERTIES` agree on `retry_count: integer` and `tags: keyword`. Provider metadata defines different global types (`long`/`flattened`), but the existing registry already selects the incident owner's types for incident indices. The historical conflict origin is that global provider union.

No current existing-environment mapping was supplied; the clean full-chain gate remains blocked before this investigation can establish installed state. Therefore no incompatible live mapping, reindex need or Team 1 migration is claimed. Retain this disposition as NOT REPRODUCED until authoritative installed evidence establishes otherwise.

### Security evidence classification and global browser gates — Team 0/5

The shared verifier's skipped-test rule and two independently opted-in security fixtures require Team 0 coordination. Do not simply set the global integration opt-in for the domain suite: it enables unrelated Elasticsearch security fixtures rather than providing that secured stack. Do not remove skips from evidence or describe these tests as passed.

Connector/Schema's prior-head full Playwright job failed; reusable Cluster Console passed. The exact prior-head [Console job 122701305848](https://github.com/Jagadeeshck/DataObs/actions/runs/40654238667/job/122701305848) confirms `strict mode violation: getByLabel('Tenant') resolved to 2 elements`, `strict mode violation: getByLabel('Workspace') resolved to 2 elements`, and axe `color-contrast` (observed contrast ratio 1.08), along with unrelated Data Product/platform journeys. Those remain Team 5 dependencies unless a current focused assertion identifies an owned defect. No shared selector, style, shell, accessibility gate or axe assertion was weakened.

## Final acceptance

Keep PR #309 **draft**. Release decision: **BLOCKED**. The seven mandatory workflows must complete successfully on one final candidate SHA, with independently accepted artifacts for that SHA. Queued, running, skipped, previous-head successful and locally passing checks are not substitutes. Final URLs/outcomes belong in the PR's exact-head run inventory; partial artifacts are diagnostic only. No environment/release publication, tag, RC freeze or supported-platform promotion was performed.
