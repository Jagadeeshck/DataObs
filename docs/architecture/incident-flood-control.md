# Incident flood control v1

Flood control is notification noise control, not ingestion control. Its safe deterministic key is scoped by tenant, environment, correlation group, signal family, source/service, and bounded event-time bucket. Durable event IDs make replay idempotent; event-time windows include both exact boundaries and tolerate out-of-order input.

States are `normal`, `elevated`, `flooding`, `recovering`, and `closed`. Count, rate, unique-asset and unique-source thresholds enter elevated/flooding states. A quiet period and lower recovery threshold provide hysteresis. Critical severity, suspected data loss, material new business impact, critical products/services, and materially expanded scope bypass coalescing. Each transition records prior/new state, thresholds, observed values, window, policy, reasons and bounded evidence references.

Coalescing targets the representative incident and increments a durable suppressed-notification count. It never implies provider delivery, rejects a finding, deletes an incident, closes lifecycle state, executes remediation, or suppresses critical escalation.

## Runtime v1 production contract

The durable runtime, storage/OCC/idempotency boundaries, deferred recovery, security bounds and current certification limitations are specified in [Incident correlation runtime](incident-correlation-runtime.md) and [Event Storm runtime](event-storm-runtime.md), with operator procedures in the corresponding operations runbooks. Correlation associates evidence without deleting incidents; flood control changes notification intent without discarding ingestion.
