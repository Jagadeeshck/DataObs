# Safe remediation runtime threat model

Protected assets are tenant action state, approvals, provider references and immutable evidence. Threats include cross-scope lookup, self-approval, stale/replayed approval, idempotency substitution, two-worker execution, malicious payloads, secret leakage and false recovery.

Controls are tenant/environment predicates, authenticated subject attribution, method-aware RBAC, exact canonical fingerprints, expiry and one-time consumption, OCC/fencing, static executor registry, strict Pydantic schemas, bounded text/pages/batches/timeouts/retries, safe references, deterministic evidence and deny-by-default provider readiness. Payload fields reject unknown data and secret/URL-like values. No dynamic imports, arbitrary network, shell, SQL or DSL exist.

Residual risk: Elasticsearch projection and stream append are not a distributed transaction. Deterministic events and reconciliation reduce duplication; uncertainty remains operator-visible. No provider executor is certified, and capability status is `functional_unvalidated` until exact-head independent evidence exists.

## Production closure v1

Safe remediation now separates the deterministic action fingerprint from a durable, generated preview instance. Live requests return the stored instance; expired requests allocate one next generation. Queueing enforces the preview actor and current catalogue/policy/target revisions.

Governed execution uses `APPROVED → RESERVED → CONSUMED`. The reservation records the deterministic execution identity before publication. Reconciliation releases only an expired reservation for which the execution projection is absent; an existing execution always causes consumption. Decision and runtime events use deterministic create-only IDs with pending evidence descriptors for partial-write repair.

Workers fence all writes. Definitely pre-submission failures may retry the same execution, unknown provider outcomes enter `RECONCILIATION_REQUIRED` and use provider lookup after takeover, and non-retryable failures terminate safely. Verification evidence must be at or after `execution_started_at` and match tenant, environment, target, action, provider reference and attempt when supplied. `verified_execution` is derived from final validation, never a provider success flag. Operator prose is length bounded and rejected when it resembles credentials.
