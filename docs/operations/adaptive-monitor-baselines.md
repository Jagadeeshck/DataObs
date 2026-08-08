# Operating adaptive monitor baselines

Use balanced sensitivity initially, at least 14 eligible observations, a bounded 60-observation/90-day window, and relevant hourly/weekday seasonality. Learning delay defaults to two evaluations. Breaches, backfills, maintenance, stale/incomplete evidence and explicit exclusions do not train the baseline according to policy.

Investigate stale or degraded state before interpreting pass results. Reset requires the existing monitor permission, authenticated principal, reason and If-Match/OCC. It creates a generation and audit event without deleting history. For persistent shifts, accept, reject or defer the generated recommendation; policy is never mutated automatically.

Rollback disables adaptive mode or returns to static thresholds. Existing observations, evaluations, findings and baseline generations remain queryable.
