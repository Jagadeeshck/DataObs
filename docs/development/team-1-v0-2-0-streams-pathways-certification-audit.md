# Team 1 v0.2.0 Streams and Pathways certification audit

## Scope

This audit covers the first-release Team 1 acceptance scope for DataObs v0.2.0. It is a defect/certification closure only: no new messaging platform, topology feature, remediation action, or product surface is added.

Audited main at branch creation: `09fa1fe615c69f79a8056772a4b424b5c564fb86`.

Working branch: `codex/release-team1-streams`.

Draft PR: #309, **Team 1: close v0.2.0 streams and pathways certification blockers**.

Release truth remains fail-closed. A local test, source fix, workflow definition, or uploaded partial artifact is not a certification result. Promotion requires successful exact-SHA hosted evidence.

## Ownership boundary

Team 1 owns the Kafka observer, pathway worker, stream/pathway product-query adapters and APIs, Stream/Pathway Console capability code, and focused Stream 360 tests. Shared migration registry mechanics, release authority, reusable workflows, shared security configuration, generated global contracts, and shared Console shell/accessibility remain Team 0/Team 5 or cross-team controlled.

Released migration definitions and checksums are immutable. No incompatible index may be deleted or recreated as a workaround.

## Hosted failure triage from current main

| Capability workflow | Current-main run | First meaningful failure | Classification | Team 1 action |
| --- | --- | --- | --- | --- |
| Pathway Intelligence backend | [40583122017](https://github.com/Jagadeeshck/DataObs/actions/runs/40583122017) | Full migration apply rejects incompatible `dataobs-data-products-v1` fields `description`, `owner`, `revision`, `tags` | Shared Team 0/Team 2 migration dependency | Do not bypass. Capability caller now installs canonical CI dependencies so deterministic fixtures can run after shared migration is repaired. |
| Stream Observer backend | [40583121972](https://github.com/Jagadeeshck/DataObs/actions/runs/40583121972) | Domain/security tests passed; release metadata step failed with `ModuleNotFoundError: packages` | Team 1 workflow invocation defect | Execute release metadata with `python -m scripts.release.release_metadata`. |
| Kafka Cluster 360 | [40583122372](https://github.com/Jagadeeshck/DataObs/actions/runs/40583122372) | Verify job blocked by shared data-product mapping; reusable backend separately failed Mypy in `services/kafka_observer` | Shared dependency + Team 1 typing defects | Fix Team 1 typing without runtime semantic changes; do not bypass migration. |
| Connector and Schema 360 | [40583122056](https://github.com/Jagadeeshck/DataObs/actions/runs/40583122056) | Exact-commit backend blocked by shared mapping; reusable backend failed same Mypy scope; broad Console Playwright includes unrelated shell/Data Product/platform failures | Shared dependency + Team 1 typing + Team 5/browser dependency | Fix owned Mypy. Retain global Playwright/axe failures as Team 5 dependency rather than weakening the gate. |
| Stream 360 Core Console | [40583122014](https://github.com/Jagadeeshck/DataObs/actions/runs/40583122014) | Migration/seed stage blocked by same data-product mapping incompatibility | Shared Team 0/Team 2 migration dependency | Rerun unchanged domain contracts after shared repair. |
| Pathway Explorer Console | [40583121939](https://github.com/Jagadeeshck/DataObs/actions/runs/40583121939) | Migration stage blocked by same data-product mapping incompatibility | Shared backend dependency; browser remains cross-team | No migration bypass. Rerun after shared repair and separate any Team 1 journey failure from Team 5 shell/accessibility failures. |

### Deterministic pathway fixture history

Earlier Pathway Intelligence runs did not establish a failing deterministic pathway assertion. In run 40524617849 the migration command was piped through `tee` without fail-fast propagation in that historical workflow state; the following fixture step then failed because `pytest` was not installed. Current main correctly uses `set -o pipefail`, which exposes the real migration incompatibility before fixtures execute.

The release branch installs both `requirements.txt` and `requirements-ci.txt` for this capability so the fixture suite can execute once the shared migration chain is green.

## Team 1 defects corrected in PR #309

- Schema Intelligence runtime repository is typed as its concrete fixed-index repository contract rather than `object`.
- Stream Intelligence runtime repository is typed as its Elasticsearch repository rather than `object`.
- Intelligence Worker runtime is typed as `IntelligenceRuntime`.
- Dataclass JSON conversion narrows dataclass instances rather than classes.
- Capacity evaluator no longer reuses `strong` for both a boolean and a signal collection.
- Scheduled Kafka collection callbacks use `functools.partial` instead of an uninferrable closure.
- Pathway Intelligence workflow installs canonical CI dependencies.
- Stream Observer invokes release metadata as a module.
- Older Team 1 capability workflows use the current forward-only `packages.elastic_store.cli apply` command instead of the legacy snapshot-oriented migration script.

These changes are intended to remove certification plumbing/type defects only; they do not alter unknown/zero semantics, introduce providers, or execute remediation.

## Supported v0.2.0 Streams / Pathways acceptance matrix

| Capability | Implementation baseline | Required semantics | Current certification state |
| --- | --- | --- | --- |
| Kafka cluster inventory | Kafka observer + Cluster 360 | tenant/environment bounded; missing evidence is unknown | implemented; hosted exact-SHA rerun pending/shared migration blocked |
| Topic inventory | Kafka observer + Stream 360 | bounded search/filter/pagination; measured zero remains zero | implemented; hosted exact-SHA rerun pending/shared migration blocked |
| Consumer-group inventory | Kafka observer + Stream 360 | scoped groups/members/assignments; no fabricated offsets | implemented; hosted exact-SHA rerun pending/shared migration blocked |
| Consumer lag | offset/high-watermark evidence | measured lag only when both offset sides exist; missing is unknown | implemented; Stream Observer domain suite passed on current main before metadata-recording failure |
| Evidence state semantics | stream/pathway contracts | zero, missing, stale, partial, unavailable and unknown remain distinct | implemented; focused hosted rerun required |
| Kafka Connect metadata | Connector 360 | safe metadata only; no credentials/raw config | implemented/optional; hosted exact-SHA backend/browser evidence pending |
| Schema Registry metadata | Schema 360 | compatibility evidence is not causal proof; no raw schema persistence/display | implemented/optional; hosted exact-SHA backend/browser evidence pending |
| Pathway node/edge projections | pathway worker | deterministic canonical identity; bounded/cycle-safe reads | implemented; blocked before hosted fixture execution by shared migration |
| Pathway latency/health/bottlenecks | pathway intelligence | explainable evidence; bottleneck candidate is not root cause | implemented; hosted deterministic fixture evidence pending |
| Stream reliability | reliability runtime | append evaluation -> OCC projection/signal -> checkpoint; no-data is not healthy | implemented; exact-SHA real-stack rerun pending |
| Pathway reliability | reliability runtime | same scoped/fenced semantics as stream reliability | implemented; exact-SHA real-stack rerun pending |
| Restart/replay | Kafka/pathway workers | durable checkpoints, lease expiry/takeover, fencing, deterministic replay | implemented in runtime contracts; exact-SHA hosted verification pending |

“Implemented” in this matrix is not equivalent to production-certified. v0.2.0 remains NO_GO until the required exact-SHA hosted gates succeed.

## Kafka migration and mapping compatibility

The current clean-stack Team 1 workflows are blocked by a shared `dataobs-data-products-v1` mapping incompatibility, not a demonstrated Kafka-index mapping incompatibility.

Repository release evidence also records a separate historical/non-clean-environment concern involving `dataobs-findings-v1` fields `retry_count` and `tags`. No retained passing/failing exact-candidate Kafka artifact currently justifies a Team 1 forward migration for that concern.

Required disposition:

1. Do not edit released migrations.
2. Do not delete or recreate `dataobs-findings-v1`.
3. Reproduce the exact installed mapping from retained evidence after the clean-install migration blocker is resolved.
4. If the installed mapping is truly incompatible with the released contract, coordinate a new forward-only migration and reindex/alias plan with Team 0 and the owning incident/storage domain.

## Console/browser dependency

The Connector/Schema reusable Console run reaches Playwright but the full-suite invocation currently reports unrelated global failures including duplicate “Workspace” labels and shared color-contrast violations, plus Data Product/platform journeys. Team 1 must not weaken axe, disable those tests, or modify shared shell/security styling solely to make its capability workflow green.

Team 1 will correct only a Stream/Pathway-specific browser assertion if a focused failure remains after Team 5/global Console stabilization.

## Cross-team dependency status

### Team 2 PR #310 — clean-install Data Product mapping repair

Team 2 has an open release-stabilisation PR, **#310 — Team 2: Stabilize v0.2.0 Quality, Job Observability and Lineage release workflows**, based on the same audited main SHA.

Its audit reproduces the clean-install defect that blocks the Team 1 capability workflows: generic mutable-index creation can pre-empt the Data Product-owned mapping for `description`, `owner`, `revision`, and `tags` on `dataobs-data-products-v1`. PR #310 changes shared `packages/elastic_store/registry.py` and adds a registry regression without editing a released migration. Team 0 review is required.

Team 1 does not duplicate this shared-registry change. Until #310 (or an equivalent Team 0-approved correction) is merged and rebased into this branch, dedicated clean-install Team 1 workflows are expected to remain blocked before their domain assertions.

### Hosted Stream Observer evidence already obtained

On PR #309 run [40652669752](https://github.com/Jagadeeshck/DataObs/actions/runs/40652669752), the `certify` job ran Elasticsearch 9.4.2 and Kafka 3.9.1 and completed the Team 1 Stream 360/security suite with **148 passed and 2 legitimate opt-in security skips**. The producer generated exact-commit product evidence and uploaded artifact **12799504917**.

Artifact: https://github.com/Jagadeeshck/DataObs/actions/runs/40652669752/artifacts/12799504917

The independent verifier then failed because the workflow passed a non-existent nested extraction directory to the verifier. GitHub's single-artifact download had extracted `metadata.json` directly into `downloaded-evidence`. PR #309 corrects the verifier directory to that actual extraction root.

This successful producer is useful real-stack/domain evidence, but it does not replace the dedicated full-migration capability workflows because Stream Observer intentionally does not apply the complete released migration chain.

## Current PR-head hosted status

Current Team 1 branch head at the latest audit update: `76fd972c285b1bc2b6402c0bb4b763747e925ed5`.

The required exact-head Team 1 workflows were queued in GitHub Actions at audit time, so no final-head PASS is claimed. Relevant queued runs:

- Pathway Intelligence backend: [40653695111](https://github.com/Jagadeeshck/DataObs/actions/runs/40653695111)
- Stream Observer backend: [40653694439](https://github.com/Jagadeeshck/DataObs/actions/runs/40653694439)
- Kafka Cluster 360: [40653694082](https://github.com/Jagadeeshck/DataObs/actions/runs/40653694082)
- Connector and Schema 360: [40653694280](https://github.com/Jagadeeshck/DataObs/actions/runs/40653694280)
- Stream 360 Core: [40653694041](https://github.com/Jagadeeshck/DataObs/actions/runs/40653694041)
- Pathway Explorer: [40653694256](https://github.com/Jagadeeshck/DataObs/actions/runs/40653694256)
- Stream and Pathway Reliability Runtime: [40653694485](https://github.com/Jagadeeshck/DataObs/actions/runs/40653694485)

Queued is not successful evidence. The PR must remain draft while mandatory final-head results are unavailable or while the shared migration dependency remains unmerged.

## Remaining blockers

1. **Shared migration chain** — `dataobs-data-products-v1` incompatibility prevents clean Elasticsearch 9.4.2 capability jobs from reaching Team 1 seed/domain assertions.
2. **Team 5/global browser quality** — shared Playwright/axe failures prevent broad Console certification from being used as Team 1 evidence.
3. **Exact-SHA reruns** — PR #309 must retain successful hosted runs for all applicable Team 1 capabilities after dependencies are repaired.
4. **Kafka existing-environment mapping concern** — must be reproduced from actual mapping evidence before any forward migration is proposed.

## Exit criteria

Team 1 release closure is complete only when the mandatory v0.2.0 Team 1 workflows succeed on one exact candidate SHA, Elasticsearch 9.4.2 and Kafka real-stack gates applicable to the capability pass, tenant/environment isolation passes, deterministic pathway fixtures pass, reliability restart/replay semantics pass, and retained evidence links identify that same candidate SHA.
