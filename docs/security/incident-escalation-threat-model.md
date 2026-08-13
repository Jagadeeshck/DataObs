# Incident escalation threat model

Trusted principal scope supplies tenant and environment. Browsers may query derived state and acknowledge an existing escalation but cannot create levels or staleness. Writes require incident-write authorization, idempotency, and OCC. Deterministic identities and atomic creates mitigate replay and notification storms. Bounded filters and aggregation limits mitigate cardinality abuse. Evidence references are bounded; raw notification payloads and secrets are never projected.
