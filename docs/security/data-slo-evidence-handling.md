# Data SLO evidence handling

All definitions, queries, cursor contexts, evaluations, and current projections bind tenant and environment. Evidence references are bounded identifiers, not raw records or credentials. Signed cursors additionally bind filters, sort, resource, and expiry. Exclusions require a trusted actor and audit reason. Definition and current-state writes use OCC; evaluation history is append-only. Logs and metrics must not contain uncontrolled asset, monitor, or SLO identifiers.
