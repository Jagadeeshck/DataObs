# Job/run observability threat model

| Threat | Controls |
|---|---|
| forged events / tenant spoofing / replay | source-bound tokens, server-side tenant/environment, deterministic IDs, rate limits, audit |
| amplification / malicious facets / cardinality | request, batch and 64 KiB facet budgets; `flattened` mapping; bounded aggregation |
| credential, variable, profile or Spark-config leakage | secret references, field allowlists, recursive redaction, TLS; never browser/Elasticsearch credentials |
| compiled SQL, rows, Kafka payloads, offsets, stack traces | fingerprints and safe references only; retention controls |
| DAG injection / unsafe actions | action/DAG/parameter allowlists, schema validation, approval, idempotency, concurrency and verification |
| cross-tenant opaque IDs | mandatory tenant/environment predicates on every lookup and action |
| event-log path traversal / SSRF | configured roots and resolved files; HTTPS and host allowlists for History Server/Airflow/dbt Cloud |
| huge Spark runs / denial of service | checkpoints, maximum events, server aggregation/sampling, query budgets/timeouts |
| stored XSS / unsafe Kibana links | output encoding, no HTML trust, allowlisted base URL and encoded state |

Residual risks require real multi-tenant, SSRF, stored-XSS, redaction and load testing. This is not a production-readiness attestation.
