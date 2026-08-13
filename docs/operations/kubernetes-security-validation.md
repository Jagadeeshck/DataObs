# Kubernetes security validation

Render with terminal migration derived by `scripts/release/render_helm_values.py`, then run `validate_kubernetes_runtime.py rendered --manifest render.yaml --allowed-registry 'ghcr[.]io'`. Run image and contract scanners separately and retain JSON output.

Cluster mode is read-only and requires namespace, release, and either explicit context or deliberate current-context acknowledgement. It requests selected non-secret object types only; it never gets Secrets or dumps kubeconfig. `UNKNOWN` is not compliant. Hosted absence remains PENDING, not PASS. Kind is functional validation only and cannot prove a customer's CNI.
