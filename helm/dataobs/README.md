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
