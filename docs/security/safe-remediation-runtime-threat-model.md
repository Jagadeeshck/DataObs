# Safe remediation runtime threat model

Protected assets are tenant action state, approvals, provider references and immutable evidence. Threats include cross-scope lookup, self-approval, stale/replayed approval, idempotency substitution, two-worker execution, malicious payloads, secret leakage and false recovery.

Controls are tenant/environment predicates, authenticated subject attribution, method-aware RBAC, exact canonical fingerprints, expiry and one-time consumption, OCC/fencing, static executor registry, strict Pydantic schemas, bounded text/pages/batches/timeouts/retries, safe references, deterministic evidence and deny-by-default provider readiness. Payload fields reject unknown data and secret/URL-like values. No dynamic imports, arbitrary network, shell, SQL or DSL exist.

Residual risk: Elasticsearch projection and stream append are not a distributed transaction. Deterministic events and reconciliation reduce duplication; uncertainty remains operator-visible. No provider executor is certified, and capability status is `functional_unvalidated` until exact-head independent evidence exists.
