# Production Kubernetes security

Install through `helm/dataobs` only. Create or label a dedicated namespace using the reference manifest, supply real release digests and allowed registry patterns, external HTTPS Elasticsearch/OIDC, referenced Secrets, and an enforcing NetworkPolicy CNI. Production Helm guardrails fail closed; placeholder digests intentionally prevent certification.

Apply no policy exception without schema-valid ownership, approval, expiry, scope and compensating control. Exceptions do not make Restricted compatibility true. Revalidate after Kubernetes/chart/CNI/ingress upgrades. Admission engines are optional, but production requires enforce-equivalent native validation.
