# DataObs Beta deployment chart

This single chart packages API, Console, five independently configured workers, optional bundled OpenTelemetry Collector, and a migration hook. It deploys neither Elasticsearch, Kibana, identity, ingress controllers, nor Collection Manager. It is **functional but unvalidated**, not production certified.

## Install

Create the referenced Elasticsearch, application, OIDC, scanner and Kafka Secrets first. Pin every image by digest, then run:

```bash
helm upgrade --install dataobs ./helm/dataobs -n dataobs --create-namespace -f helm/dataobs/values-production.yaml
```

`values-minimal.yaml`, `values-external-otel.yaml`, and visibly non-production `values-development.yaml` are overlays on defaults. The external cluster must support Elasticsearch 9.4.2 APIs and grant runtime least privilege; the migration identity additionally manages templates, indices/data streams, aliases and mappings. No secret value belongs in values: only Secret names and keys are rendered.

Digests take precedence over tags. NetworkPolicy is enabled and requires a compatible CNI; add explicit egress CIDRs for databases, Kafka, Connect, Schema Registry, OIDC, Elasticsearch and external OTel. API and Console have two replicas, rolling updates, topology configuration, PDBs and optional HPAs. OTel defaults to two replicas. Every worker defaults to one replica; despite leases in pathway/Kafka runtimes, horizontal and rollout-overlap safety is not certified.

The migration Job executes `python -m packages.elastic_store.cli apply` once as a pre-install/pre-upgrade hook with a deadline and retained completion logs. Disable only under a controlled external migration process. Helm rollback restores Kubernetes resources; it never reverses Elasticsearch schema changes.

Console runtime configuration is a ConfigMap-backed browser object containing only API URL and public OIDC settings. Immutable assets remain nginx-served; Elasticsearch is never browser-exposed. API probes use `/readyz` and `/livez`; Console uses `/healthz`; OTel uses port 13133. Workers expose no HTTP service.

See the Kubernetes production guides and `docs/development/beta-deployment-packaging-audit.md` for security, permissions, exclusions, sizing and failure diagnosis.
