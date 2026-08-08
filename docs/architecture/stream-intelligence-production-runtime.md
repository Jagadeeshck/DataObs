# Stream Intelligence production runtime

The v1 runtime reuses `packages.streaming.intelligence`: historical observers produce typed evidence, the existing algorithms evaluate it, and the runtime persists immutable evaluation evidence before OCC projections, transition signals, and finally the detector checkpoint. A failed intermediate operation leaves the checkpoint unmoved and therefore reconcilable.

Detector state is durable in the current anomaly projection: `normal`, `watch`, `anomalous`, `severe`, `recovering`, `insufficient_data`, `stale`, `error`, or `disabled`. Counters are loaded before every evaluation. Missing evidence is not zero, stale evidence is not normal, and estimated/inferred samples retain their label.

SHA-256 identities include tenant, environment, resource type/id and detector where applicable. Mutable writes validate a monotonically increasing lease fence and use `_seq_no`/`_primary_term`. A replacement worker increments the fence, causing an old worker's next mutation to fail. Immutable writes use create-only semantics for replay idempotency.

Transition signals are emitted for confirmed, severe, recovering, and recovered state changes rather than every evaluation. Their content is metadata and evidence references only. Reliability objective status remains an independent fact. Nearby changes are correlated events or possible contributing changes, never causal claims.
