# DataObs Kubernetes Manifests

These manifests provide a quick-start Kubernetes deployment for DataObs core services.

## Included components
- `Namespace` (`dataobs`)
- `ConfigMap` for DataObs and OTEL collector settings
- `Deployment` + `Service` for DataObs API
- `Deployment` for DataObs quality engine
- `Deployment` + `Service` for OTEL Collector

## Apply

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/otel-collector.yaml
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/service-api.yaml
kubectl apply -f k8s/deployment-quality.yaml
```

## Notes
- This setup assumes an existing Elasticsearch endpoint; update `ELASTICSEARCH_URL` env vars.
- For production usage, use the Helm chart in `helm/dataobs/` and external Secrets.
- AWS telemetry collection requires IAM permissions for CloudWatch/X-Ray and `AWS_REGION` on the collector pod.
