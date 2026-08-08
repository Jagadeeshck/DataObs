# Canonical platform deployment model

## Classification and boundary

The **canonical** product model is DataObs application workloads installed by `helm/dataobs` on Kubernetes, backed by an **externally managed Elasticsearch** cluster. Elasticsearch is not a subchart or DataObs-managed lifecycle resource. OpenSearch is a different product and is not a supported substitute.

The DataObs control plane comprises API, Console, quality and scanner workers, monitor runtime, pathway worker, Kafka observer, migration Job, and the chart's optional OpenTelemetry collector. Platform operations is part of the API. External dependencies are Elasticsearch, OIDC provider, external OTLP gateway when selected, secret provider, registry, snapshot object storage, DNS, and ingress/load balancer. DataObs stores references, never their credentials.

```
Platform
  └── Platform Environment (development/integration/staging/production)
        └── Kubernetes Cluster
              └── DataObs Helm Installation
                    └── Tenant
                          └── Tenant Environment Scope (development/test/UAT/production)
```

A Kubernetes cluster, DataObs installation, tenant environment, platform environment, and Elasticsearch cluster are distinct identities. One installation may serve multiple logically isolated tenants. Physical separation is an explicit profile, not the default.

## Ownership

Helm owns application workloads and Kubernetes contracts. Operators own cluster authentication, ingress, DNS and secrets. Elasticsearch operators own availability, snapshots and recovery. OIDC owns identity. Terraform may create prerequisites but cannot duplicate Helm or apply production changes from PR CI.
