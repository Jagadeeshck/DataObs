# Beta deployment packaging audit

Audited against the post-PR #184 `main` merge (`754046c`). The terminal immutable migration is `0021_lineage_analysis_explorer`. Commands below come from production Dockerfile `ENTRYPOINT`/`CMD`, not source-layout inference.

| Component | Dockerfile | Effective command | Port / readiness / liveness | Configuration, secrets, Elasticsearch access | Helm status |
|---|---|---|---|---|---|
| API | `Dockerfile.api` | `python -m src.api.main` | 8080; `/readyz`; `/livez` | endpoint, tenant/environment, OIDC, OTel, logging/timeouts; ES username/password/CA and cursor/signing/encryption Secrets; index/data-stream read/write, alias and migration-status read | packaged |
| Console | `ui/dataobs-console/Dockerfile` | unprivileged nginx image default | 8080; `/healthz`; `/healthz` | runtime API URL and public OIDC metadata; no credentials and no ES access | packaged |
| Quality Worker | `Dockerfile.quality` | `python -m src.quality.engine` | none | ES/tenant/OTel; ES Secret; quality index read/write | packaged, single replica |
| Scanner Worker | `Dockerfile.scanner` | `python -m services.scanner_worker.cli --config /etc/dataobs-scanner/config.yaml run` | none | projected source definition and database credential Secrets, TLS, schedule/concurrency/allowlist; ES read/write | packaged, single replica |
| Monitor Runtime | `Dockerfile.monitor-runtime` | `python -m services.monitor_runtime.cli run` | none (CLI health command only) | ES/tenant/OTel Secret; monitor definitions/state read/write | packaged, single replica |
| Pathway Worker | `Dockerfile.pathway-worker` | `python -m services.pathway_worker.cli run` | none | ES/tenant/OTel Secret; pathway projections and leases read/write | packaged, single replica |
| Kafka Observer | `Dockerfile.kafka-observer` | chart overrides image default diagnostic command with `python -m services.kafka_observer.cli run` | none | Kafka bootstrap/SASL/TLS, optional Connect and Registry Secrets; ES projections/checkpoints/leases read/write | packaged, single replica |
| OTel Collector | upstream contrib image | `--config=/etc/otel/collector.yaml` | 4317/4318; health 13133 | ES Secret and optional TLS; telemetry indices/data streams write | optionally bundled |
| Migration Job | `Dockerfile.api` | `python -m packages.elastic_store.cli apply` | none; Job completion | ES administrator Secret; templates, indices/data streams, aliases, mappings and migration metadata manage | pre-install/pre-upgrade hook |

All Python commands were import/CLI-help checked without changing behavior. Worker probes are deliberately omitted because these processes do not listen. On restart work resumes from persisted state. Pathway and Kafka code has lease semantics, but rollout overlap has not been scale-certified; all workers therefore remain one replica. No worker HPA or PDB implies unsupported HA.

## Exclusions and gaps

Elasticsearch is external-only. Kibana, an identity provider, ingress controller, Grafana Alloy, demos, and POCs are excluded. Collection Manager has no dedicated production Dockerfile/entrypoint and is not packaged. External source CIDRs cannot be inferred and must be configured. Hosted Kind, upgrade, load, and independent evidence remain required before production certification.
