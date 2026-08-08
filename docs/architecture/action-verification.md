# Action verification

Provider acceptance is not execution proof and execution success is not recovery. An accepted action enters `verification_pending`. Evidence must be durable, bounded, match the target, and have an observation time after execution began.

`scan_task_v1`, `freshness_measurement_v1`, and `connection_test_v1` are declared strategies, but their executors remain unconfigured until a safe public service contract is certified. Verification records `verified_execution` separately from nullable `recovery_observed`; missing evidence is failure/pending, never success. No verification resolves an incident automatically.

## Production closure v1

Safe remediation now separates the deterministic action fingerprint from a durable, generated preview instance. Live requests return the stored instance; expired requests allocate one next generation. Queueing enforces the preview actor and current catalogue/policy/target revisions.

Governed execution uses `APPROVED → RESERVED → CONSUMED`. The reservation records the deterministic execution identity before publication. Reconciliation releases only an expired reservation for which the execution projection is absent; an existing execution always causes consumption. Decision and runtime events use deterministic create-only IDs with pending evidence descriptors for partial-write repair.

Workers fence all writes. Definitely pre-submission failures may retry the same execution, unknown provider outcomes enter `RECONCILIATION_REQUIRED` and use provider lookup after takeover, and non-retryable failures terminate safely. Verification evidence must be at or after `execution_started_at` and match tenant, environment, target, action, provider reference and attempt when supplied. `verified_execution` is derived from final validation, never a provider success flag. Operator prose is length bounded and rejected when it resembles credentials.
