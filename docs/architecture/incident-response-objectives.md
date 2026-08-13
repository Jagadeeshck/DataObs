# Incident response objectives

Incident response objectives are Team 3 policy snapshots and do not extend Team 2's Data Reliability SLO definition. A definition keeps the duration target (for example, 300 seconds) separate from its population objective (for example, 0.95). Supported metrics are acknowledge, investigation, mitigation, recovery, and resolution.

Eligibility creates an immutable assignment containing the definition revision, effective time, derived deadline, source incident revision, policy version, and canonical snapshot hash. A tighter policy may replace an unbreached assignment; a relaxation never extends its deadline and a proven breach is permanent.

The centrally versioned approaching-breach threshold is 80 percent. Missing event time is never interpreted as zero: active work is pending or breached based on the deadline, while completed incomplete evidence is unavailable. Every result exposes evidence status, coverage, and reason codes.

Evaluation delegates error-budget and burn arithmetic to `packages.domain_model.slo`; a 100 percent objective therefore retains canonical `zero_error_budget` behavior.
