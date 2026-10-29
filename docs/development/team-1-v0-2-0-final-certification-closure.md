# Team 1 v0.2.0 final certification closure

## Scope

Team 1 — Streams and Pathways

Branch: `codex/v020-team1-certification-closure`

Audited integrated `main`:

`f62acd9f0d32ec827c26b7c8ccc56b18ac0c9401`

This is release certification only. No new stream, pathway, messaging, reliability, remediation, topology or Console feature is introduced.

Previously merged Team 1 release closure:

- PR #309 — **Team 1: close v0.2.0 streams and pathways certification blockers**
- merge commit: `36e3a873fd9baac05e286db55f5f3bfe255c10de`

Shared dependencies that were open during PR #309 are now merged:

- Team 0 PR #311
- Team 2 PR #310
- Team 4 PR #314
- Team 5 PR #315

Certification must therefore be re-evaluated against the integrated repository rather than inferred from PR #309 evidence.

## Current integrated hosted triage

The following runs are from the integrated main candidate and are diagnostic evidence only. They are not exact-head evidence for this certification branch.

| Capability | Run | First meaningful failure | Ownership / disposition |
| --- | --- | --- | --- |
| Stream Observer backend | [40862723897](https://github.com/Jagadeeshck/DataObs/actions/runs/40862723897) | Team 1 domain/security step reports 3 failures in `tests/security/test_gate0_oidc_runtime.py`: legacy rule list/search/delete allow implicit cross-tenant access | Team 0 security/runtime dependency. Team 1 does not alter legacy rule authorization or weaken the security suite. |
| Pathway Intelligence backend | [40862723969](https://github.com/Jagadeeshck/DataObs/actions/runs/40862723969) | Full migration application fails: `Incompatible existing mapping on dataobs-data-product-revisions-v1: revision` | Shared Team 0/Team 2 storage dependency. No Team 1 registry workaround. |
| Kafka Cluster 360 | [40862724184](https://github.com/Jagadeeshck/DataObs/actions/runs/40862724184) | Exact capability job fails at the same Data Product revision mapping conflict | Shared storage dependency. Reusable Team 1 backend validation passes. |
| Connector / Schema 360 | [40862724306](https://github.com/Jagadeeshck/DataObs/actions/runs/40862724306) | Exact capability job fails at the same Data Product revision mapping conflict | Shared storage dependency. Reusable Team 1 backend validation passes. |
| Stream 360 Core | [40862724180](https://github.com/Jagadeeshck/DataObs/actions/runs/40862724180) | Migration/seed step fails at the same Data Product revision mapping conflict | Shared storage dependency. |
| Pathway Explorer | [40862723973](https://github.com/Jagadeeshck/DataObs/actions/runs/40862723973) | Backend stage fails at the same Data Product revision mapping conflict | Shared storage dependency. |
| Cluster / Connector reusable Console validation | jobs in runs above | TypeScript typecheck and ESLint pass; Prettier fails only on Team 5-owned `e2e/certification/existing-journeys.spec.ts`, `e2e/console.spec.ts`, `e2e/fixtures/release.ts`, `e2e/release-critical-journeys.spec.ts`, `e2e/supportability.spec.ts` | Team 5 / shared Console formatting dependency. Team 1 does not rewrite shared E2E files to make a capability caller green. |

## Stream Observer evidence

The integrated Stream Observer producer reaches the Team 1 Stream 360 and security suite.

Run 40862723897 reports:

- **229 passed**
- **3 failed**
- **2 skipped**

The three failures are all Team 0-owned legacy rule tenant isolation assertions:

- `test_legacy_rules_reject_implicit_cross_tenant_access[list]`
- `test_legacy_rules_reject_implicit_cross_tenant_access[search]`
- `test_legacy_rules_reject_implicit_cross_tenant_access[delete]`

The two skips are the independently opted-in Data Product Elasticsearch security tests already documented in the prior Team 1 audit.

This result confirms the previously corrected Team 1 source regressions, including:

- capacity runtime / bottleneck contract using `CapacityBottleneck.candidate`;
- stream lag correctness tests;
- zero / missing / stale / unknown distinctions;
- stream/pathway reliability unit contracts;
- tenant-isolation tests owned by Team 1;
- replay/idempotency regressions owned by Team 1.

It does **not** make Stream Observer certified because the selected security suite still fails.

## Capacity runtime contract

The current capacity regression asserts the real contract:

`mixed.bottleneck_candidates[0].candidate == "provider_ingress"`

The domain type is:

`CapacityBottleneck(candidate, confidence, reason_codes, evidence_refs)`

No `dimension` field is expected.

The prior release defect that asserted `.dimension` is therefore closed on integrated main.

## Required certification semantics

The release candidate must continue to preserve:

- measured zero != missing;
- missing != healthy;
- stale != current;
- unknown != zero;
- estimated/inferred != measured;
- pressure != provider saturation;
- backlog growth != provider saturation;
- dependency != impact;
- bottleneck candidate != root cause.

Kafka lag remains valid only when the required offset evidence exists.

Pathway latency must not become zero when evidence is missing.

Reliability checkpointing must remain last after durable evidence/projection/signal writes.

## Team 1 capability matrix — integrated pre-PR state

`PASS` means the specific dimension has direct evidence.
`BLOCKED` means certification cannot proceed to that dimension because an earlier mandatory shared gate failed.
No prior-head result is promoted as exact-head certification for this branch.

| Capability | Source/unit contract | Integrated Team 1 backend | ES 9.4.2 full-chain | Kafka real-stack | Tenant isolation | Console/browser | Exact-head certification | Current state |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kafka cluster/topic inventory | PASS | PASS | BLOCKED | prior Team 1 proof exists; rerun required | PASS | BLOCKED | pending | BLOCKED |
| Consumer groups / lag | PASS | PASS | BLOCKED | prior Team 1 proof exists; rerun required | PASS | BLOCKED | pending | BLOCKED |
| Zero / missing / stale / unknown | PASS | PASS | BLOCKED | PASS in prior focused proof | PASS | focused contracts PASS | pending | BLOCKED |
| Capacity / saturation semantics | PASS | PASS | BLOCKED | not required for every provider | PASS | focused contracts PASS | pending | BLOCKED |
| Pathway deterministic assembly | PASS | not reached in current exact workflow | BLOCKED | NOT_APPLICABLE | PASS in focused tests | BLOCKED | pending | BLOCKED |
| Pathway replay / watermarks / fencing | PASS | not reached in current exact workflow | BLOCKED | NOT_APPLICABLE | PASS in focused tests | NOT_APPLICABLE | pending | BLOCKED |
| Stream/pathway reliability | PASS | PASS in selected domain suite | BLOCKED | NOT_APPLICABLE | PASS | focused contracts PASS | pending | BLOCKED |
| Connector metadata/privacy | PASS | reusable backend PASS | BLOCKED | NOT_APPLICABLE | PASS | shared formatting/browser dependency | pending | BLOCKED |
| Schema metadata/privacy | PASS | reusable backend PASS | BLOCKED | NOT_APPLICABLE | PASS | shared formatting/browser dependency | pending | BLOCKED |

## Shared dependencies

### Data Product revision mapping

Current full-chain Elasticsearch 9.4.2 application fails on:

`dataobs-data-product-revisions-v1.revision`

This is not a Team 1 index or mapping.

Team 1 must:

1. retain the exact error;
2. hand it to Team 0/Team 2;
3. rebase when the approved shared repair lands;
4. rerun the full released migration chain;
5. never delete the incompatible index;
6. never add a duplicate global registry workaround;
7. never modify a released migration/checksum.

### Legacy rule cross-tenant security

The current Stream Observer suite exposes a Team 0 security failure where tenant A can list/search/delete tenant B legacy rules when no tenant selector is explicitly supplied.

Team 1 must not narrow the security suite, xfail the assertions, or change legacy-rule authorization.

This remains a mandatory release dependency.

### Shared Console formatting / browser evidence

Current reusable Console jobs pass TypeScript typecheck and ESLint, then fail Prettier on five Team 5-owned E2E files.

Team 1 may fix a focused Streams/Pathways component defect if one appears after the shared formatting gate is green.

Team 1 must not weaken Prettier, Playwright, axe, accessibility, browser matrix or shared shell requirements.

## Certification actions for this branch

1. Trigger all mandatory Team 1 pull-request workflows on the exact branch head.
2. Record the first meaningful failure for every failed job.
3. Fix only Team 1-owned domain defects.
4. Re-run focused Team 1 unit/security suites after any source fix.
5. Re-run Kafka real-stack validation where the workflow reaches it.
6. Re-run Elasticsearch 9.4.2 full-chain persistence once the shared migration gate is repaired.
7. Run applicable Team 5 browser journeys without altering shared browser quality rules.
8. Retain exact-SHA run/artifact links.
9. Update the capability matrix to PASS/BLOCKED/FAIL/NOT_APPLICABLE only.
10. Leave the PR draft until every mandatory Team 1 capability is independently verified.

## Release decision at branch creation

**BLOCKED**

Reason:

- shared Elasticsearch mapping conflict occurs before multiple Team 1 domain fixtures;
- Team 0 legacy-rule tenant isolation assertions fail in Stream Observer certification;
- shared Team 5 E2E formatting blocks reusable Console validation;
- exact-head certification for this branch has not yet run.

No Team 1 feature expansion or speculative workaround is justified by the currently observed failures.
