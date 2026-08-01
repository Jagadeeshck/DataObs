# Operating incident correlation and flood control

Monitor bounded counters for evaluations, group creates/attachments, insufficient evidence, OCC retries, failures, flood transitions, late events, coalescing, bypasses and deferred reconciliation. Metric dimensions are limited to result, policy version, severity band, flood state, reason family and retry outcome; never use tenant, incident, asset, evidence or error text.

On dependency failure, preserve the finding and incident and report `incident_persisted_correlation_deferred` or `incident_persisted_flood_evaluation_failed`. Reconciliation replays the same deterministic decision/event ID. OCC recovery refetches state, recomputes the pure merge, and avoids duplicate membership and counts. Operators must verify aliases, strict mappings, stream templates, retention and backlog before enabling production writers.

All accepted findings and incidents remain stored. Flood control only changes notification decisions and group presentation. No external notifier or remediation adapter is enabled by this feature.

## Certification

Unit and focused repository tests do not certify Elasticsearch restart persistence or strict-mapping compatibility. Run the opt-in Elasticsearch 9.4.2 suite before production enablement and record its output; do not infer success from mocked clients.
