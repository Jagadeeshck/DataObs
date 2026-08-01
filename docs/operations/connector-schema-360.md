# Operating Connector and Schema 360

Use `/streams/connectors/:connectorId` with `stream-connectors:read` and `/streams/schemas/:subjectId` with `stream-schemas:read`. Both are read-only, refresh manually, cancel obsolete requests, reset with context changes, and preserve complete, partial, stale, not-configured, unknown and unavailable evidence. No restart, remediation, monitor creation, raw configuration, full-schema view or unrestricted download is provided.

Connector health is healthy only for RUNNING with measured zero failures, warning for PAUSED, critical for FAILED, degraded for observed failed tasks, and unknown otherwise. Staleness changes data status rather than rewriting health. Schema compatibility is registry evidence, not a guarantee; fingerprint-only changes remain unknown for breaking classification. Impact relationships display their evidence relationship and confidence and never infer from subject names.

The feature is implemented for beta-1 but remains `functional_unvalidated` until exact-commit hosted Elasticsearch, browser, Playwright and axe evidence is independently verified.
