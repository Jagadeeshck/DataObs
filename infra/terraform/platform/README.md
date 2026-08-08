# AWS supported-reference prerequisites (unvalidated)

This root documents an optional EKS target: private subnets across at least three AZs, multi-AZ managed nodes, optional AWS Load Balancer Controller/external DNS/Secrets Store CSI integration, and externally supplied OTLP and Elasticsearch references. It does **not** provision Elasticsearch or OpenSearch and does not install DataObs; `helm/dataobs` remains the application contract. Terraform authentication, backend and Kubernetes credentials are operator-managed.

This is `supported_reference` architecture but hosted product certification is pending. Validation does not make AWS or EKS a supported-platform entry.
