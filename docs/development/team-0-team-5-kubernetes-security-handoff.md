# Team 5 Kubernetes security handoff

A future Console may display only target SHA, overall state, mandatory passed/failed/unknown counts, generated time, and report identifier. It must not receive Kubernetes objects, pod environment, Secret data, kubeconfig, registry credentials, admission responses, or cluster metadata. `UNKNOWN` and hosted `PENDING` must remain visibly distinct from PASS.
