# Remediation effectiveness v1

Team 3 projects one bounded episode per structured action/workflow execution. Provider completion, authoritative Safe Remediation verification, recovery timing, resolution, reopen, and recurrence remain separate evidence. `verified_effective` requires provider success and verification success; provider success without verification is `inconclusive`; authoritative verification failure is `no_observed_effect`; provider failure is `failed`; timeout/reconciliation/unknown is `outcome_unknown`; later authoritative invalidation is `contradicted`.

Episode IDs bind tenant, environment, incident, execution and definition version. Coverage reports six independent evidence categories. Recovery-after-action is a temporal association, never causal attribution. Overlapping interventions preserve verified target effect while marking incident recovery attribution ambiguous.
