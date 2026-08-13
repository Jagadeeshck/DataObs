# Remediation effectiveness threat model

Tenant and environment are trusted-principal filters on every read and aggregation. Browser input cannot set provider, verification, effectiveness, recurrence, episode identity or raw Elasticsearch DSL. Filter/group fields and date ranges are allowlisted and bounded. Projections contain references and normalized statuses only—never provider bodies, logs, SQL, credentials, tokens, workflow secrets or comments. Telemetry labels are limited to result, class and intervention type; record and tenant identifiers are prohibited.
