# Data SLO production runtime

Only active definitions are due. Workers request at most 200 runtime rows ordered by `next_evaluation_at,slo_id`, acquire a time-bounded lease with a monotonically increasing fence, resolve canonical evidence for the exact definition revision, invoke `data-reliability-v1`, append the deterministic evaluation, update current state only while holding the fence, then checkpoint. A replay with identical evidence is a no-op; changed evidence produces a different immutable identity.

Operators should stop workers on repeated lease conflicts or Elasticsearch unavailability. Never delete evaluation streams during recovery and never insert raw business rows as evidence references. Metrics must use state, SLI family, and environment dimensions only—not SLO, asset, monitor, contract, or job identifiers.
