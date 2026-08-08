# Safe Remediation Runtime v1 closure audit

## Baseline and preflight

The audited baseline is `ee8bb0363df503e60c85136f6d46ecb6ce606633` (merge PR #224). The repository snapshot contains PR #217, PR #219 and merged PRs #220–#224. Network fetch of the private origin was attempted before editing but credentials were unavailable; the local first-parent history was therefore the auditable latest `main` snapshot. PR #219's complete merge diff and the subsequent Team 0 route-policy and Team 5 Console changes were inspected. The starting terminal migration was dynamically reported by `scripts/release/current_terminal_migration.py` as `0026_stream_anomaly_retention_intelligence`.

The focused baseline suite (`tests/incidents/test_safe_remediation_runtime.py` and `tests/unit/test_incident_automation.py`) passed 9 tests. Strict resources were inspected in `packages/elastic_store/manifest.py`: the approval and idempotency projections use strict top-level fields plus bounded `flattened` metadata; approval, remediation and verification data streams accept the existing event envelope. No migration is needed for keyword state values or flattened metadata.

## Finding closure

| Review finding | Current-main reproduction | Root cause | Fix | Regression test | Status |
| --- | --- | --- | --- | --- | --- |
| One approval publishes two executions (P1) | Reproduced | Execution was created before approval OCC consumption | OCC `APPROVED → RESERVED`, deterministic approval-bound execution, then `CONSUMED` | `test_one_approval_cannot_publish_two_executions` | Closed |
| Reservation partial writes (P1) | Reproduced by failure boundary | No reservation state/reconciler | Expiring reservation plus deterministic publication reconciliation | `test_reserved_approval_recovers_after_crash`, `test_execution_creation_reconciles_reserved_approval` | Closed |
| Executor exception strands `RUNNING` (P1) | Reproduced | Exceptions escaped `run_once` | Typed safe/uncertain/terminal failures, redacted stable codes and per-item isolation | `test_executor_exception_does_not_kill_worker`, `test_uncertain_provider_outcome_is_not_blindly_retried` | Closed |
| Expired execution lease/fencing (P1) | Reproduced | Only queued work was discoverable | Expired incomplete lookup, lease takeover, provider lookup and fence on every update | `test_expired_running_lease_is_recoverable`, `test_old_fencing_token_cannot_update_execution` | Closed |
| Approval request required approval permission (P1) | Reproduced | Broad incident-automation write rule | Explicit method-aware execute/approve rules precede family rules | `test_operator_can_request_approval`, `test_operator_cannot_approve`, `test_approver_can_decide`, `test_reader_cannot_request_action` | Closed |
| Required incident state ignored (P2) | Reproduced | Only negative denylist evaluated | Non-empty positive allowlist fails closed first | `test_required_incident_states_are_enforced` | Closed |
| Blast radius used five-item sample (P1) | Reproduced | API used `len(detail["affected_assets"])` | Detail exposes authoritative count separately and preview consumes it | `test_full_asset_count_escalates_risk` | Closed |
| Preview conflict returned fictional expiry (P1) | Reproduced | Deterministic ID conflated action and instance | Stable action fingerprint plus atomically persisted generation; conflicts return durable instance | `test_identical_live_preview_returns_durable_instance`, `test_expired_preview_creates_next_generation`, `test_concurrent_preview_refresh_converges` | Closed |
| Pre-execution evidence verifies (P1) | Reproduced | Compared to queue creation | Explicit execution start and evidence binding | `test_pre_execution_evidence_cannot_verify` | Closed |
| Failed validation says verified (P1) | Reproduced | Event copied provider success flag | `verified_execution` derives only from final state | `test_wrong_target_success_flag_is_unverified`, `test_stale_success_flag_is_unverified` | Closed |
| Approval decision event lost (P1) | Reproduced | Projection and event were independent without repair descriptor | Deterministic pending decision event, idempotent retry and reconciliation | `test_approval_decision_event_recovers_after_append_failure`, `test_conflicting_second_approval_decision_fails` | Closed |
| Rerun scan targets affected asset (P2) | Reproduced in Console flow | Browser supplied first asset and incident revision | Server resolves scanner/monitor/integration IDs and revisions from incident evidence and revalidates selections | `test_rerun_scan_uses_real_scanner_target`, `test_ambiguous_scanner_requires_server_resolved_selection` | Closed |
| Preview actor transferable (P1) | Reproduced | Queue omitted actor comparison | Exact preview/queue actor binding | `test_preview_actor_must_match_execution_actor` | Closed |
| Approval prose stores credentials (P1) | Reproduced | Only length validation | Reusable control-character and credential-pattern rejection without echo/log | `test_secret_in_approval_reason_is_rejected`, `test_secret_in_approval_comment_is_rejected` | Closed |
| Expired approved remains approved (P2) | Reproduced | Queue only raised expiry | OCC expiry projection and deterministic event | `test_expired_approved_approval_persists_expired_state` | Closed |

## State machines and recovery

Approval states are `REQUESTED → APPROVED → RESERVED → CONSUMED`, with `REQUESTED → REJECTED`, and nonterminal requested/approved records able to expire. A reservation binds approval, action fingerprint, preview, requester/executor, deterministic execution, request, start and expiry. If publication is absent after reservation expiry, release to `APPROVED` is safe because provider submission cannot precede the execution projection. If the execution exists, reconciliation only consumes; it never releases. Terminal states never return to requested.

Execution states are `QUEUED → CLAIMED → RUNNING`. A definitely pre-submission failure returns the same execution ID to `QUEUED` within retry limits. Unknown provider outcome enters `RECONCILIATION_REQUIRED`; a takeover calls `lookup()` and never blindly submits. Known terminal failures enter `FAILED`; accepted work enters `VERIFICATION_PENDING`, followed by `VERIFIED` or `VERIFICATION_FAILED`. Each takeover increments the fencing token, so a stale owner cannot update. Runtime timeout begins at `execution_started_at`, not `queued_at`.

## Failure matrix

| Injected boundary | Durable intermediate state | Reconciliation outcome |
| --- | --- | --- |
| Reserve succeeds / execution create fails | `RESERVED`, deterministic execution absent | After reservation expiry, restore `APPROVED`; no provider could have run |
| Execution create succeeds / consume fails | `RESERVED`, deterministic execution present | Consume reservation; never publish a second execution |
| Decision succeeds / event append fails | Decision state plus pending deterministic descriptor | Retry/reconciler create-only appends event, then clears pending |
| Execution update / event append fails | New execution state plus deterministic pending event ID | Append can be retried create-only; state is not rolled back |
| Verification update / event append fails | Final verification state plus deterministic pending event ID | Append can be retried; false success is impossible |
| Crash after `RUNNING` | Expiring fenced lease | Takeover enters lookup/reconciliation |
| Crash after provider acceptance | `RUNNING`/uncertain with expired lease | Lookup by same execution identity; never resubmit blindly |
| Crash before operation reference persistence | Uncertain state, same execution/attempt | Provider lookup resolves identity or remains reconciliation-required |

## Security and mapping conclusions

Tenant and environment are checked on every projection fetch. The action fingerprint binds catalogue hash, policy hash, actor, incident revision, target revision and payload. Approval binds the exact preview and fingerprint; execution binds the same actor. Server-side target resolution rejects arbitrary browser IDs. Free text is bounded and rejected for credential, bearer/JWT, connection string and private-key patterns. Event IDs are deterministic and Elasticsearch appends use create-only semantics.

No released migration was edited and no forward migration was required. Starting and ending terminal migration are both `0026_stream_anomaly_retention_intelligence`.

## Validation record

* Focused backend closure: 117 passed, 2 real-Elasticsearch security tests skipped by their opt-in guards.
* Compile, Ruff, Black, route permission, team boundary, generated-artifact, documentation-link and migration-immutability checks passed.
* The prescribed aggregate paths `services/workflows` and `tests/workflows` do not exist in this baseline; equivalent checks ran against all present Team 3 and shared paths.
* Capability-ledger validation reports the pre-existing unrelated missing `/quality/*` Console route.
* Console API generation, typecheck, lint, formatting and 52-test Vitest suite passed. The generated schema was not committed because the baseline OpenAPI artifact regenerates broad unrelated Team 5 changes and makes the existing quality feature fail project build. Console build/bundle validation remains blocked by those pre-existing quality exports/types, not incident automation.
* A browser screenshot was attempted, but the installed Playwright package had no browser and the environment denied the Chromium download with HTTP 403. The development server also reports the same unrelated quality-module export failures.
* Elasticsearch 9.4.2 was not available, so the opt-in real-stack certification was not reported as passed.
