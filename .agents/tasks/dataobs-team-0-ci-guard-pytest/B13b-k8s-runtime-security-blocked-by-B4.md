# B13b — K8s runtime security evidence blocked by B4 (Kind packaging blocker)

Status: BLOCKED — downstream of B4, NOT fixed here, NOT an independent defect.

## Summary
The "Team 0 Kubernetes runtime security v1" workflow's `static-security` job fails at:

    build_kubernetes_security_evidence.py ... --input kind-functional-report.json

The `kind-functional-report.json` input is produced by the Kind smoke test. That
smoke is the already-documented **B4 fail-closed NO_GO** (hosted-runner Kind
resource limit). Because the functional report is never produced, the K8s runtime
security evidence step has no input and fails.

## Why this is not fixed here
- B13b is strictly **downstream of B4**. It is not an independent workflow defect:
  the YAML is correct; its required input is missing because B4's Kind smoke cannot
  run on the current hosted runner.
- Per repository safety rules, we do **not** fabricate the missing
  `kind-functional-report.json`, do **not** add `|| true`, and do **not** weaken or
  skip the evidence check to make the job green.

## Resolution condition
B13b resolves only when **B4's Kind smoke runs on an adequately-sized runner at the
frozen SHA**, producing a real `kind-functional-report.json`. At that point the K8s
runtime security evidence step can consume a genuine functional report and pass on
its own merits. No change to the K8s runtime security workflow is required for B13b
itself — it is gated entirely by the B4 Kind blocker.

## Reference
- B4: Kind packaging / hosted-runner resource-limit fail-closed NO_GO (pre-existing).
- B13b observed in: "Team 0 Kubernetes runtime security v1" workflow, `static-security` job.
