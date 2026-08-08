# Safe remediation control plane

The v1 control plane is explicitly human-governed: catalogue → deterministic preview → optional independent approval → idempotent queue → fenced worker → verification. Catalogue and policy hashes bind every stage. High/prohibited actions are denied; unavailable internal adapters are `not_configured`, never successful.

Only a static server registry can resolve executors. There is no generic shell, Python, HTTP, SQL, ES|QL or Elasticsearch executor. Preview performs validation and policy only and has no provider side effect. Execution never changes incident lifecycle state.

Mutable approvals use OCC. Operation IDs bind tenant, environment, incident, action fingerprint and caller idempotency key. Claims increment a fencing token and expire after a bounded lease. Every transition has a deterministic immutable evidence ID. Projection/evidence writes are not transactionally atomic, so reconciliation replays missing evidence and never requeues an uncertain provider operation.

## Production closure v1

Safe remediation now separates the deterministic action fingerprint from a durable, generated preview instance. Live requests return the stored instance; expired requests allocate one next generation. Queueing enforces the preview actor and current catalogue/policy/target revisions.

Governed execution uses `APPROVED → RESERVED → CONSUMED`. The reservation records the deterministic execution identity before publication. Reconciliation releases only an expired reservation for which the execution projection is absent; an existing execution always causes consumption. Decision and runtime events use deterministic create-only IDs with pending evidence descriptors for partial-write repair.

Workers fence all writes. Definitely pre-submission failures may retry the same execution, unknown provider outcomes enter `RECONCILIATION_REQUIRED` and use provider lookup after takeover, and non-retryable failures terminate safely. Verification evidence must be at or after `execution_started_at` and match tenant, environment, target, action, provider reference and attempt when supplied. `verified_execution` is derived from final validation, never a provider success flag. Operator prose is length bounded and rejected when it resembles credentials.
# Production runtime safety additions

Running provider calls use independently renewed, owner-checked fenced leases. Target selection is bounded and
finding-backed; current revisions are reloaded from the owning capability rather than accepted from the browser or
incident evidence. A worker that loses its fence cannot persist provider results, verification, or timeline evidence.

## Authoritative target and deadline boundary

Production previews resolve finding-backed targets through the composed bounded owner resolver. Execution reloads
the incident and target revisions; browser values never establish current authority. Heartbeat renewal is bounded
by `execution_started_at + timeout_seconds`, after which lease expiry permits a newly fenced worker to reconcile an
uncertain provider outcome. A stale worker cannot publish its late result.
