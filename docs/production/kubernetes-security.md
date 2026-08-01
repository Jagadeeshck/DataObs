# Kubernetes security

Pods default to non-root, RuntimeDefault seccomp, all capabilities dropped, no privilege escalation, read-only roots and no service-account token. Dedicated accounts have no RBAC. Credentials are never generated or copied into ConfigMaps. NetworkPolicy defaults deny unlisted paths while allowing DNS and configured namespace/CIDR traffic; actual enforcement depends on the CNI. Rotate referenced Secrets through the organisation's secret manager. Confirm image signatures, SBOMs and provenance from the release manifest.
