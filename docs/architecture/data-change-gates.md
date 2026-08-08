# Data change gates

The Team 2 change-gate package performs deterministic, provider-neutral evaluation of safe dbt metadata before deployment. Explicit states distinguish `partial`, `unknown`, and `missing` from success. Checks retain reason codes, confidence, aggregate metrics and evidence states. Advisory mode preserves blocking evidence but reports a warning; enforced mode reports deterministic failures.

Risk is `100 * weighted mean(available bounded components)`. Missing components are excluded and exposed; confidence is reported separately. Contract and lineage checks are adapter boundaries to the existing canonical engines and never infer absent evidence.
