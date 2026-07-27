# DataObs Helm Chart

## Install

```bash
helm upgrade --install dataobs ./helm/dataobs -n dataobs --create-namespace
```

## Key values
- `api.enabled`: deploy API service
- `quality.enabled`: deploy quality engine
- `otelCollector.enabled`: deploy collector (disable when reusing existing OTEL infra)
- `config.dataobsYaml`: inline DataObs product configuration
- `config.otelCollectorYaml`: inline OTEL collector config

## Reuse existing OTEL and Elasticsearch
Set:

```yaml
otelCollector:
  enabled: false

config:
  dataobsYaml: |
    deployment:
      telemetry_mode: external_otel
      storage_mode: external_elasticsearch
    external_otel:
      enabled: true
      endpoint: "https://otel-gateway.company.net:4317"
    elasticsearch:
      existing_cluster: true
      url: "https://es-prod.company.net:9200"
```

## Packaging status and immutable versions

This chart is a deployment **foundation**, not a production-ready installation. It currently packages only the DataObs API, quality worker, and an optional OpenTelemetry Collector. Console, scanner, monitor-runtime, pathway-worker, Kafka-observer, Collection Manager, Elasticsearch, Kibana, identity, HA, and backup/restore lifecycle are not managed by this chart.

The checked-in `0.1.0` image tags are placeholders aligned with the chart application version, not a recommendation to deploy that release. For an actual release candidate, override each repository and pin the exact semantic tag or, preferably, digest from `dataobs-release-manifest.json`; never deploy `latest`:

```bash
helm upgrade --install dataobs ./helm/dataobs \
  --set api.image.tag=1.2.3 \
  --set quality.image.tag=1.2.3
```

The images and chart are proprietary software owned by KJC InfoTech Limited and distributed only under the repository's All Rights Reserved licence.
