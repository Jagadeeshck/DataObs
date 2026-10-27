# Team 4 Google Pub/Sub messaging collector v1 audit

* **Team:** Team 4 — Integrations & Collection.
* **Audited base:** `2281a64034b915f4f7dd556cd582f27e30660a1c` on 2026-10-12.
* **Migrations:** graph valid with 33 migrations; dynamically derived terminal is
  `0033_team1_stream_schema_intelligence_runtime`; release metadata and Helm consistency checks pass. Migration doctor
  is represented by the valid graph/release checks. Immutability uses the event-aware resolver against the audited
  base. No migration is required: generic observations and Team 1 storage already exist.
* **Registry:** before: aws, snowflake, databricks, bigquery, azure, trino, presto, postgres, mysql, mariadb, sqlserver,
  oracle, rabbitmq. After: the same providers plus independent `gcp` v1; BigQuery remains `bigquery`.
* **Team 1 boundary:** `PubSubAdapter` already establishes `provider=gcp`, `messaging_system=google_pubsub` and topic,
  subscription and dead-letter-topic resource kinds. The observation envelope is reused. Multi-broker runtime currently
  persists resources but does not project every metrics/backlog/retention/DLQ family; this gap is untouched.
* **Existing Google foundation:** BigQuery supplies proven ADC, WIF, impersonation, reference-only legacy-key and
  redaction patterns. It was inspected but not refactored. No other GCP Collection Manager provider existed.
* **GA dependencies checked at task time:** google-cloud-pubsub 2.42.0, google-cloud-monitoring 2.32.0, google-auth
  2.61.0, google-api-core 2.42.0. They remain optional.
* **IAM:** predefined Pub/Sub Viewer and Monitoring Viewer, or the documented narrow list/get custom permissions.
* **Pagination:** explicit project/resource/page/observation/series/point/time limits; no organization discovery.
* **Metrics:** fixed regional backlog-first and safe delivery/request allowlists; missing differs from zero and metric
  kind/window is preserved. `topic/send_request_count` remains request count.
* **Known limitations:** Pub/Sub Lite, snapshots, payloads, schema bodies, IAM policies, event-driven collection and
  Team 1 metric-family projections are out of scope. Live Google Cloud/IAM/Monitoring and independent verification are
  not run. State is at most `functional_unvalidated`; DataObs remains `NO_GO`.
