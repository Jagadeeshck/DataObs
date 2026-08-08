# Stream Intelligence data handling

Every stored document is tenant/environment/resource scoped. APIs derive scope and actor from authenticated product context, use bounded fixed aliases/field allowlists and reject caller DSL. Mutations use idempotency, OCC/ETags and audit evidence.

The capability never reads or retains message payloads or keys, credentials, connector secrets, personal data, arbitrary source documents or sensitive stack traces. Failure fingerprints are deterministic hashes of normalized bounded error classifications. Partition identifiers are capped; reason and evidence references are bounded.

Missing evidence remains missing. Estimated and inferred values are labelled. Failure findings use “candidate”; overlays use non-causal wording; future loss is not asserted. Team 1 signals are redaction-safe and do not write to Team 3 private indexes or trigger remediation.

