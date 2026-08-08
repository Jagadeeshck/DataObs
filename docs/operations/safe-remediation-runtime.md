# Safe remediation runtime operations

The worker consumes at most 25 durable queued operations, claims via OCC/fencing, performs at most the catalogue retry count, and persists the provider reference before verification. Unknown executors fail closed. Operators must investigate expired leases and use provider lookup before changing uncertain state; never blindly requeue an accepted operation.

This repository supplies the runtime state machine but no certified provider executor at this baseline. Deployment and scheduling remain Team 0 responsibilities. Health must report queued count, oldest age and lease conflicts without tenant/incident metric dimensions.

## Production closure v1

Safe remediation now separates the deterministic action fingerprint from a durable, generated preview instance. Live requests return the stored instance; expired requests allocate one next generation. Queueing enforces the preview actor and current catalogue/policy/target revisions.

Governed execution uses `APPROVED → RESERVED → CONSUMED`. The reservation records the deterministic execution identity before publication. Reconciliation releases only an expired reservation for which the execution projection is absent; an existing execution always causes consumption. Decision and runtime events use deterministic create-only IDs with pending evidence descriptors for partial-write repair.

Workers fence all writes. Definitely pre-submission failures may retry the same execution, unknown provider outcomes enter `RECONCILIATION_REQUIRED` and use provider lookup after takeover, and non-retryable failures terminate safely. Verification evidence must be at or after `execution_started_at` and match tenant, environment, target, action, provider reference and attempt when supplied. `verified_execution` is derived from final validation, never a provider success flag. Operator prose is length bounded and rejected when it resembles credentials.
