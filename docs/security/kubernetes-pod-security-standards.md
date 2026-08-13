# Kubernetes Pod Security Standards

The canonical Helm workloads target Kubernetes 1.30 and are statically compatible with **Baseline** and **Restricted**: non-root, RuntimeDefault seccomp, no privilege escalation, read-only roots, and all capabilities dropped. The validator covers every regular and init container and rejects host namespaces and hostPath. There are no known production exceptions.

The namespace reference pins `v1.30`, matching the chart's deliberately narrow range. Re-evaluate allowed seccomp, capabilities, volume and probe behavior before changing `kubeVersion`. Helm does not create or mutate customer namespaces. Restricted admission is enforcement evidence only when the namespace labels are applied by the operator and observed. Static rendering cannot prove admission or CNI behavior.
