# Distribution drift detection

V1 stores aggregate profiles only. Numerical profiles contain count, null count, five canonical quantiles, at most 100 canonical histogram buckets and outlier ratio. Comparison returns dispersion-normalized quantile movement, null/outlier changes, Jensen–Shannon divergence and PSI. Equal bucket shapes are required; smoothing prevents zero divisions and non-finite output.

Categorical profiles are deterministically sorted by descending count then label, capped at 50 categories and include `OTHER`. Classification policy may replace labels with `REDACTED`. Comparison aligns the union of bounded labels, distinguishes zero counts from absent evidence, and identifies appearance or disappearance of categories with at least ten percent share. Raw rows are never accepted or stored.
