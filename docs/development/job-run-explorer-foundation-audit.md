# Job and Run Explorer foundation audit

Base SHA: `6793b91` (merge of PR #94). The repository had no configured Git remote in this environment; that commit itself confirms PR #94 was merged. The immutable migration chain ended at `0007_automated_monitoring_data_products_rca`; this change adds forward-only `0008_job_run_observability`.

| Concern | Current state | Gap | Required action in this PR | Test evidence |
|---|---|---|---|---|
| OpenLineage endpoint/auth | Legacy data-observability handler was not source-bound | dedicated endpoint and tenant binding absent | dedicated bearer source binding; payload tenant ignored | unit contract |
| RunEvent/JobEvent/DatasetEvent | partial legacy RunEvent parsing | Job/Dataset events absent | accept all three stable shapes | unit contract |
| Unknown facets | no bounded durable contract | mapping explosion risk | preserve within 64 KiB `flattened` field | unit contract |
| Duplicate/order | no deterministic lifecycle projection | replay and COMPLETE-before-START | canonical SHA-256 event IDs and terminal precedence | unit contract |
| Job/run/task storage | protocol/model foundation only | durable job-specific resources absent | migration indices, streams and latest transforms | manifest tests; ES 9.4.2 pending |
| Job monitor APIs | shared monitor runtime exists from #94 | job links and runtime endpoints incomplete | reuse v2 monitor definitions; add job link projection | integration pending |
| Incident/RCA | shared incident/RCA models exist | run evidence correlation incomplete | preserve incident/RCA references; service boundary | integration pending |
| Spark | instrumentation helpers existed | event-log replay/stage analysis absent | bounded replay reader, aggregation and skew method | unit tests |
| dbt roadmap | basic integration test existed | artifacts/OpenLineage reconciliation absent | artifact readers and reconciliation key | unit tests |
| Console routes | command center/asset/pathway foundations | Pipelines/Job/Run routes absent | API/domain foundation in slice; Console work pending | browser pending |
| Migrations | `0007` latest; checksum protected | job resources absent | append immutable `0008` only | migration unit tests |
| CI | broad project CI exists | real Airflow/dbt/Spark/browser jobs absent | document blockers; do not claim DoD | real-stack jobs pending |

PR #94 delivered a limited runtime foundation, not source-provider, migration, UI, browser, or real integration completion. This audit intentionally leaves those items pending where this vertical slice does not prove them.
