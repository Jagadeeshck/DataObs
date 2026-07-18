# Pathway and asset threat model

The primary threats are cross-tenant traversal, graph enumeration, arbitrary entity identifiers, unsafe saved filters, Kibana URL injection, annotation stored XSS, excessive traversal, monitor/workflow privilege escalation, sensitive query text, payload/key leakage and source-reference leakage.

Controls are mandatory tenant/environment filters before traversal, bounded request models, server-side Elasticsearch access, escaped text rendering, allowlisted Kibana origins, query fingerprinting/redaction, scoped mutation permissions, ETag concurrency and audit events. Workflow actions must be non-destructive or approval-gated. Credentials, database rows, raw SQL, Kafka payloads and message keys are prohibited from product responses.

Known limitations remain documented in the backend audit; these controls do not constitute a production-readiness claim.
