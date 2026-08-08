# Safe remediation control plane

The v1 control plane is explicitly human-governed: catalogue → deterministic preview → optional independent approval → idempotent queue → fenced worker → verification. Catalogue and policy hashes bind every stage. High/prohibited actions are denied; unavailable internal adapters are `not_configured`, never successful.

Only a static server registry can resolve executors. There is no generic shell, Python, HTTP, SQL, ES|QL or Elasticsearch executor. Preview performs validation and policy only and has no provider side effect. Execution never changes incident lifecycle state.

Mutable approvals use OCC. Operation IDs bind tenant, environment, incident, action fingerprint and caller idempotency key. Claims increment a fencing token and expire after a bounded lease. Every transition has a deterministic immutable evidence ID. Projection/evidence writes are not transactionally atomic, so reconciliation replays missing evidence and never requeues an uncertain provider operation.
