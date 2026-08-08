# Action approval response

Confirm tenant, environment, incident/target revisions, exact impact, risk, expiry, catalogue hash and separation-of-duty status. Reject if evidence is missing or the blast radius is unclear. Comments are bounded and must not contain credentials.

For conflicts, refresh instead of repeating a stale decision. For expiry, create a new preview and request. For `not_configured`, do not bypass the registry. After execution, distinguish queued, accepted, verification pending, verified execution, and recovery observed. Follow rollback guidance honestly; v1 does not promise automatic rollback.

## Production closure v1

Safe remediation now separates the deterministic action fingerprint from a durable, generated preview instance. Live requests return the stored instance; expired requests allocate one next generation. Queueing enforces the preview actor and current catalogue/policy/target revisions.

Governed execution uses `APPROVED → RESERVED → CONSUMED`. The reservation records the deterministic execution identity before publication. Reconciliation releases only an expired reservation for which the execution projection is absent; an existing execution always causes consumption. Decision and runtime events use deterministic create-only IDs with pending evidence descriptors for partial-write repair.

Workers fence all writes. Definitely pre-submission failures may retry the same execution, unknown provider outcomes enter `RECONCILIATION_REQUIRED` and use provider lookup after takeover, and non-retryable failures terminate safely. Verification evidence must be at or after `execution_started_at` and match tenant, environment, target, action, provider reference and attempt when supplied. `verified_execution` is derived from final validation, never a provider success flag. Operator prose is length bounded and rejected when it resembles credentials.
