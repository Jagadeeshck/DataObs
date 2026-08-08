# Team 3 Cases and Workflows runtime v1 closure audit

## Preflight and provenance

The audited base is `d006339b3f855b67a63bd4625d42d2f1688a354c`; the terminal migration reported dynamically by
`scripts/release/current_terminal_migration.py` is `0029_team2_data_intelligence_reconciliation`; and the latest
merged change in the supplied history is PR #243. Fetching `origin/main` and reading GitHub PR/review APIs were
attempted before edits, but the private repository required credentials. The supplied merge commits and full diffs
for PRs #219, #230, #235, and #241 were inspected locally. The complete first-parent history after #241 contains
PRs #238, #237, and #243; their diffs do not close the Team 3 findings below.

The exact strict mapping assembled from `BASE_PROPERTIES` and `INCIDENT_AUTOMATION_PROPERTIES` was inspected for
Case links, action idempotency, Workflow bindings/executions and the four requested event streams. No migration is
needed: the deterministic link is the Elasticsearch `_id`, `elastic_case_id` is the mapped remote identity, and the
bounded `metadata` field is already `flattened`.

Baseline before edits: `123 passed, 2 skipped` (the skips require opt-in real Elasticsearch security infrastructure).

## PR #241 closure table

| PR #241 finding | Severity | Reproduced on latest main | Root cause | Fix | Regression test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Case document violates strict mapping | P1 | Yes | Writer emitted `case_link_id` and `case_id` although only `elastic_case_id` is mapped | Use `_id`, mapped remote ID, supported envelope fields, and `_id` sort | `test_case_link_document_uses_only_mapped_fields`, reservation and remote-ID tests | Closed internally |
| Authoritative resolver disconnected | P1 | Yes | Preview used redacted evidence and execution echoed browser revisions | Routes use the composed bounded resolver; execution reloads incident and target | Route contract plus resolver tests | Closed internally; owner adapters remain deployment composition |
| State helpers corrupt enum | P1 | Yes | Unvalidated `model_copy` updates used strings | Typed transition table rejects illegal edges | state-helper and round-trip tests | Closed |
| Malformed nested Workflow entries ignored | P2 | Yes | Recursive walker skipped scalar/null values | Every container and entry is structurally validated before capability allowlisting | adversarial recursive tests | Closed |
| Candidate bound falsely means ambiguity | P2 | Yes | Merely reaching `max_candidates` set truncation | Truncation now requires unprocessed references; incomplete uniqueness has its own reason | boundary tests | Closed |
| Heartbeat keeps hung call alive | P1 | Yes | Renewal had no execution-deadline bound | Renewal ends at the action deadline and never extends beyond it; fence loss suppresses final evidence | deadline and fencing tests | Closed internally |

## Case repository audit

Reservations use deterministic create-only document IDs. Conflicts are idempotent only for the same scoped
reconciliation identity; mismatches fail closed. Reads enforce tenant, environment and Kibana space. Updates use
Elasticsearch sequence number and primary term and typed states. Optional dates and the remote ID are omitted when
null; dates serialize as ISO-8601. Searches query the mapped remote ID and use `_id` as the deterministic tie-breaker.
The semantic round trip through the flattened metadata envelope is tested. Concurrent in-memory reservation is also
tested; real Elasticsearch concurrency remains an opt-in certification gate.

The legal transition table permits create reservation to submitted/linked/reconciliation, submitted or
reconciliation to linked, and linked/sync states through explicit sync or remote-missing paths. In particular,
`LINKED -> CREATE_RESERVED` is rejected.

## Production target authority

Preview loads the scoped current incident, checks the browser's expected incident revision, calls the application-
composed `BoundedActionTargetResolver`, resolves finding-backed identity through the owning capability reader, and
binds the returned current revision. It does not use the legacy evidence helper. Execution accepts no client
"current" revisions: it loads the durable preview, reloads the scoped incident, calls `reload()` for the preview-
bound target, and supplies those server values to the coordinator's stale-preview check. Missing composition is a
503; stale/unavailable authority is a scope-safe conflict rather than an unhandled 500.

## Lease safety

`execution_deadline = execution_started_at + timeout_seconds` is distinct from the rolling lease deadline. A
heartbeat renews only before that deadline and caps each lease at it. At timeout it reports fence loss locally and
stops renewal, allowing expiry and takeover. The next fenced owner must reconcile provider outcome rather than
blindly resubmit. A late old call observes heartbeat/fence loss and cannot write result or terminal evidence; OCC
conflict is expected per-item behavior and does not stop the batch worker.

## Workflow validation and remaining runtime scope

Supported Workflow step containers (`branches`, `then`, `else`, `steps`, `do`, `workflow`, `sub_workflow`) accept
only objects/lists containing typed steps. Scalars, nulls, untyped objects, unknown actions, generic HTTP/Kibana,
shell/script/exec, destructive Cases actions, and deprecated aliases fail closed at any depth.

Binding persistence, binding resolution, remote checksum/drift enforcement, a Safe Remediation Workflow executor,
execution persistence/polling, verification, and Console integration are not complete production features on this
base. They remain a later feature task and are not claimed by this correctness closure. Provider mutation flags
remain opt-in and no default was changed.

## Certification and migrations

Elasticsearch 9.4.2, Kibana 9.4.2, and browser certification were **not run** because no hosted stack or credentials
were supplied. Internal strict-envelope tests are not represented as real-stack evidence. Starting and ending
terminal migration is `0029_team2_data_intelligence_reconciliation`; no released migration or checksum is changed.
