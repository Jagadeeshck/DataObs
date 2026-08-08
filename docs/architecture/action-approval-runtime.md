# Action approval runtime

Approval states are `requested`, `approved`, `rejected`, `expired`, `cancelled`, and `consumed`. A request binds one preview, incident and target revision, normalized payload fingerprint, catalogue/policy hash, requester, tenant and environment. It expires no later than its preview.

Requesters cannot decide their request, approvers require the method-aware decision permission, and an approver cannot execute the governed action. Decisions use projection revision/OCC and append immutable events. Approved records are consumed once while queueing; rejected, expired, cancelled and consumed records cannot be revived or reused.

## Production closure v1

Safe remediation now separates the deterministic action fingerprint from a durable, generated preview instance. Live requests return the stored instance; expired requests allocate one next generation. Queueing enforces the preview actor and current catalogue/policy/target revisions.

Governed execution uses `APPROVED → RESERVED → CONSUMED`. The reservation records the deterministic execution identity before publication. Reconciliation releases only an expired reservation for which the execution projection is absent; an existing execution always causes consumption. Decision and runtime events use deterministic create-only IDs with pending evidence descriptors for partial-write repair.

Workers fence all writes. Definitely pre-submission failures may retry the same execution, unknown provider outcomes enter `RECONCILIATION_REQUIRED` and use provider lookup after takeover, and non-retryable failures terminate safely. Verification evidence must be at or after `execution_started_at` and match tenant, environment, target, action, provider reference and attempt when supplied. `verified_execution` is derived from final validation, never a provider success flag. Operator prose is length bounded and rejected when it resembles credentials.
