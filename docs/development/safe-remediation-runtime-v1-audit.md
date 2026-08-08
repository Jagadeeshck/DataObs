# Safe remediation runtime v1 baseline audit

## Audited baseline

The audited starting commit is `c5b7dff6573b6fd0ce76122e7112b726c35d431d`. Fetching `origin/main` was attempted before editing but GitHub required credentials unavailable in this environment; the local first-parent history ends at merged PR #218 and contains no later implementation of this scope. The terminal migration is `0025_stream_pathway_reliability_production_closure`. No migration is added or modified.

Reviewed complete repository patches for PR #187 (`43ec068`), PR #202 and its closure findings (`915dcd2`), PR #209 (`51f4df4`), and PR #217 (`df45238`). PR #217 did not receive an automated Codex review because the review quota was exhausted. Subsequent first-parent changes were PR #218; no subsequent Team 0 or Team 5 merge exists in the available baseline.

## Focused PR #217 correctness/security review

The review traced scope predicates, strict storage serialization, coordinator deferral, flood decisions, event IDs, route authorization and Console truthfulness. No Team 3 P0 remained. A pre-existing P1 in the adjacent action-control surface was confirmed: preview treated membership in `SAFE_ACTIONS` as executable authorization, always reported low risk and retained process-local production approval/action dictionaries. The new catalogue/preview/runtime replaces that authority and fails unconfigured actions closed. PR #217's correlation runtime itself retained mandatory tenant/environment predicates, bounded queries and fail-safe deferred processing. A lower-priority limitation remains: Elasticsearch cannot atomically update projections and append evidence; deterministic event IDs and reconciliation are required.

| Finding | Severity | Root cause | Fix | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Allowlist implied execution readiness | P1 | `SAFE_ACTIONS` conflated name recognition and provider readiness | Immutable catalogue plus policy/provider decision; all uncertified adapters return `not_configured` | `test_catalogue_and_preview_are_canonical_deterministic_and_fail_closed` | Closed |
| Preview risk always low | P1 | No contextual server policy | Versioned policy escalates production critical/blast-radius actions and denies high risk | `test_risk_escalates_and_critical_suppression_is_denied` | Closed |
| Approval/action compatibility dictionaries in ES repository | P1 | Durable adapters had not been implemented | Explicit ES approval and operation adapters with OCC and strict mapped envelopes | approval/OCC and idempotency tests | Closed for the new runtime; legacy methods remain non-executable |
| User payload was untyped/unbounded | P1 | Preview accepted arbitrary dictionaries | Frozen Pydantic payload model, unknown-field rejection, bounded identifiers, secret/URL rejection | preview schema test | Closed |
| Approval reuse/self-approval | P1 | Legacy approval decision lacked binding, expiry and actor separation | Exact fingerprint, tenant/environment, expiry, OCC, separation and consumed state | approval lifecycle test | Closed |
| Provider acceptance could appear final | P1 | No execution/verification state machine | Acceptance transitions only to `verification_pending`; recovery is separate evidence | worker/verification test | Closed |

## Existing surface and exact gaps

The current catalogue was a loose `SAFE_ACTIONS` set plus a small unrelated `services/action_executor` catalogue. Workbench preview checked set membership, redacted only payload key names, always emitted `risk=low`, and correctly warned that providers were unconfigured. Legacy approvals supported basic separation but only an in-memory repository in this composition; execution deliberately raised because no safe adapter existed. Existing APIs expose workbench list/detail/timeline/mutations/preview; Console has an Actions preview panel but no durable queue/detail. Exact gaps were version/fingerprint binding, contextual policy, strict payloads, durable approval/OCC, execution idempotency and fencing, verification evidence, and honest catalog availability.

## Storage inspection

Released strict resources share `INCIDENT_AUTOMATION_PROPERTIES` plus bounded flattened `metadata`, `annotations` and common timestamp/scope fields:

* `dataobs-action-approvals-v1`: mutable approval projection (tenant, environment, incident, action/risk/approval state, request/revision/expiry/terminal fields).
* `dataobs-action-idempotency-v1`: immutable previews and mutable operation/lease projection.
* `dataobs-workflow-definitions-v1`, `dataobs-workflow-executions-v1`, `dataobs-case-links-v1`: audited but not repurposed because their semantics do not improve the action projection.
* `logs-dataobs.approval_event-*`, `logs-dataobs.remediation_action-*`, `logs-dataobs.verification_event-*`: immutable transition evidence.
* `logs-dataobs.workflow_execution-*` and `logs-dataobs.workflow_step-*`: audited, unused by this internal action runtime.
* Incident timeline currently uses `logs-dataobs.incident_comment-*`; automation evidence has deterministic IDs and can be projected by a reconciler without embedding payloads.

Generated aliases are `-read` and `-write` for mutable resources. Streams use the released wildcard templates and `-default` write names. Supplementary immutable contract values are stored only under bounded flattened metadata. Credentials, raw payloads, provider documents and stack traces are forbidden.

## Security, ownership and migration decision

Identity is derived only from `request.state.principal.subject`; route middleware supplies tenant and environment scope. The implementation adds method-aware catalogue/approval policy, strict payloads, exact fingerprints, approval expiry and separation, one-time consumption, idempotency conflicts, leases/fences, bounded batches/retries/timeouts, static executors, redacted references and scope-safe lookups. It provides no shell, dynamic import, URL, HTTP, SQL or arbitrary DSL executor and makes no incident lifecycle mutation.

Team 3 changes are restricted to incident automation services, incident API composition/policy, Team 3 tests, Console incident files when applicable, and capability documents. No provider private internals, deployment packaging, reusable CI or released migration is changed. Existing flattened metadata safely represents mandatory state, so the terminal migration remains `0025`.

## Certification

Status remains `functional_unvalidated`: local tests are not independent exact-head hosted evidence. The Elasticsearch 9.4.2 and hosted browser/axe suites require external services and retained artifacts before any Beta/production claim.
