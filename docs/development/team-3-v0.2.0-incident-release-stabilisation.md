# Team 3 v0.2.0 incident release stabilisation

## Scope

Team 3 is stabilising incident lifecycle, correlation, notification-delivery evidence, tenant boundaries, and safe automation for the DataObs v0.2.0 first release.

Audited base: `09fa1fe615c69f79a8056772a4b424b5c564fb86`.

Release branch: `codex/release-team3-incidents`.

Pull request: #312.

The base Incident Workbench certification workflow passed. This release work preserves that behavior and does not change Team 0 release infrastructure.

## Main-CI triage

The main `CI` run contained one Team 3-specific mandatory blocker:

- `Incident migration and OCC gate` stopped in its focused Mypy check with 16 errors across nine Team 3 files.

Those errors were type-safety/narrowing issues in post-incident analytics, correlation storage/service/runtime, recurrence, and safe-automation verification/reconciliation. The release branch fixes them without intentionally changing incident decisions or automation policy.

The broad `incident-automation` test job also inherited two repository-wide failures that are outside Team 3 ownership:

- generated capability documentation drift;
- the API foundation tenant-creation test receiving `403` instead of its historical `201`.

These are recorded as shared blockers rather than being bypassed or weakened in Team 3.

## Release evidence matrix

| Area | Existing evidence | Release expectation |
| --- | --- | --- |
| Incident creation/deduplication | incident repository and quality-to-incident integration tests | preserve deterministic incident identity and occurrence counting |
| Lifecycle/state transitions | Incident Workbench tests | preserve legal transitions, acknowledgement, ownership and closure rules |
| Timeline/collaboration | Workbench closure tests | append-only events, redaction, idempotent recovery |
| OCC/idempotency | Incident Workbench + migration/OCC gate | stale revisions fail; retry does not duplicate mutation |
| Correlation | correlation/flood suites | deterministic grouping, scope isolation and replay |
| Flood control | flood suites | coalescing is scoped; critical bypass preserved |
| Notifications | safe mock integration + release no-network regression | Slack/PagerDuty/ServiceNow outcomes persisted without secrets; duplicate incidents do not redeliver |
| Security | Incident Workbench/security suites | principal actor attribution, tenant/environment isolation, unauthorized action denial |
| Safe automation | safe-remediation suites | approvals, separation of duties, fencing, uncertain-provider recovery, no unrestricted executor |
| Browser | Team 5 handoff | final Incident Workbench browser acceptance must be retained separately |

## Notification retry boundary

v0.2.0 does not perform blind automatic retries after an external notification attempt returns an exception. For Slack and ServiceNow, an exception or timeout cannot prove that the external system did not already apply the side effect; blindly retrying could create duplicate responder notifications/incidents.

The supported release behavior is therefore:

1. deliver only for a newly created incident;
2. persist a redaction-safe per-channel outcome;
3. suppress duplicate delivery when the same incident occurrence is deduplicated;
4. never persist provider credentials or exception messages;
5. report a failed/unknown delivery honestly.

A durable provider-aware retry/reconciliation queue is a post-v0.2.0 enhancement unless separately implemented and certified. This limitation must not be represented as successful delivery.

## Safe automation boundary

The release remains approval-bound and deny-by-default. Existing runtime tests cover approval separation, one-time consumption, revision checks, fencing, expired-lease recovery, verification, reconciliation, and uncertain provider outcomes. Unknown provider outcomes are not blindly retried. No shell, arbitrary URL, SQL, dynamic import or unrestricted executor is introduced by this release work.

## Cross-team coordination

Team 2 release PR #310 has been notified that `tests/integration/test_quality_signal_path.py` is the cross-team quality-to-incident evidence path and must retain tenant/environment scope and redaction-safe evidence.

Team 0 release PR #311 has been notified that the dedicated Incident Workbench workflow is green on the audited base but is main/workflow-dispatch scoped, so final-head exact-SHA Incident Workbench evidence must be run explicitly rather than inferred.

No active Team 5 v0.2.0 release PR was found during preflight. Final browser/accessibility acceptance remains a Team 5 handoff.

## Restrictions

This work does not:

- add autonomous remediation;
- add notification platforms;
- weaken authorization, redaction, OCC or evidence validation;
- edit Team 0 release workflows;
- claim hosted evidence that has not executed.
