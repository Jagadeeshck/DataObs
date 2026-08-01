# Stream reliability data handling

Tenant and environment come from authenticated request context and trusted selectors, never request bodies. Actors come from the authenticated principal. Every Elasticsearch read includes tenant and environment filters, a fixed index alias, a source allowlist or exclusion, deterministic sorting, and a bounded size. Mutable definitions use ETags and require `If-Match`; stale revisions return 412.

Evidence references are bounded identifiers, not full source documents. Connector configuration, credentials, tokens, and arbitrary evidence objects are not persisted or logged. Reliability signals contain scoped resource identity, status transition, observed value, threshold/operator, timestamps, severity, reason codes, bounded references, coverage, confidence, and schema version. They remain in `logs-dataobs.reliability-signal-*`; there is no direct Team 3 private-index writer and no remediation.
