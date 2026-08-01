# Kubernetes installation

Prerequisites are Kubernetes 1.27+, Helm 3, a NetworkPolicy-capable CNI, externally managed Elasticsearch 9.4.2, an OIDC provider, signed digest-pinned images, and pre-created Secrets. Validate and install with `helm lint helm/dataobs` and `helm upgrade --install`. The chart never installs Elasticsearch, Kibana, identity, certificates, or an ingress controller. Uninstall removes Kubernetes workloads and configuration; external Elasticsearch data and externally managed Secrets remain.
