# Current production readiness

* **Active candidate source:** `d4f511ebb331b74528426b91ce69bd24f8993eac`
* **Terminal migration:** `0030_team1_multi_broker_messaging_runtime`
* **Application / chart:** `0.2.0` / `0.2.0`
* **Release decision:** **NO_GO**
* **Supported platforms:** none (`supported: []`)

This is the active evidence-derived view. Implemented and locally tested are not
synonyms for hosted tested, certified, or supported.

| Area | State | Evidence-derived status |
|---|---|---|
| Architecture | implemented | External Elasticsearch/OIDC and Helm topology contracts exist. |
| Migrations | local_tested | Registry terminal and dependency ordering derive locally; hosted clean apply/repeat is pending. |
| Storage | implemented | Elasticsearch repositories and strict migrations exist; secured hosted proof is pending. |
| IAM | local_tested | OIDC/RBAC controls exist; disposable issuer conformance is pending. |
| Tenancy | local_tested | Enforcement exists; hosted adversarial isolation is pending. |
| Security | local_tested | Fail-closed and redaction coverage exists; candidate security smoke is pending. |
| Kubernetes | blocked | No retained exact-SHA cluster deployment or candidate-artifact install. |
| Scale | pending | No retained capacity-profile result. |
| HA | unsupported | No HA profile may be advertised as supported. |
| Backup | local_tested | Snapshot tooling exists; hosted backup evidence is pending. |
| Restore | blocked | Destructive disposable restore and integrity proof are absent. |
| Upgrade | unsupported | There is no prior formally supported predecessor. |
| DR | unsupported | Functional simulations are not real hosted DR certification. |
| Operations | local_tested | Runbooks/support tooling exist; hosted behavior is pending. |
| Release | blocked | Exact-SHA evidence, immutable artifacts and installation proof are absent. |
| Supply chain | blocked | Candidate SBOM, scans, provenance and signatures do not exist. |
| Licensing | pending | Candidate dependency inventory/policy and any required review are absent. |
| Browser/accessibility | pending | Exact-SHA hosted browser/accessibility capture is absent. |

Platform support is distinct from capability support. Integrations and
capabilities remain supported, preview, experimental, or unvalidated according
to their own retained evidence; this closure does not promote them.
