# Platform troubleshooting and support-case contract

1. Identify DataObs version and release SHA. 2. Preserve `X-Request-ID`. 3. Read `/api/v1/platform/support`. 4. Inspect existing health views. 5. Read `/api/v1/platform/diagnostics`. 6. Filter `/api/v1/platform/known-issues`. 7. Select the registered runbook. 8. Collect the allowlisted support bundle. 9. Escalate using the reason code and ownership matrix. 10. Preserve checksummed evidence.

A support case should include version, release SHA, request ID, safe configuration fingerprint, affected component, SEV classification, start time, known-issue ID when applicable, and support-bundle ID. Never attach credentials, customer datasets, raw JWTs, unrestricted logs, environment dumps, Kubernetes Secrets, kubeconfig, or authorization headers. Do not run ad-hoc Elasticsearch commands; follow the registered bounded diagnostic/runbook path.
