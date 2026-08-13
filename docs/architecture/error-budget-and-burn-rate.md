# Error budgets and burn rates

Formula version: `data-reliability-v1`.

For objective *O* and *E* eligible intervals, allowed bad intervals are `E × (1 − O)`. Consumed budget is the bad count; remaining budget is allowed minus bad. Remaining percentage is `1 − bad / allowed`. No eligible denominator produces unknown values, not zero.

Observed burn is `(bad / eligible) / (1 − objective)`. A 100% objective has zero budget: any bad interval exhausts it and burn is null with reason `zero_error_budget`; APIs never serialize NaN or infinity.

Multi-window classification requires both windows for sustained signals: 2× is slow, 6× is fast, and 14.4× is critical. A single window at or above 1× is elevated. Missing either window is unknown. These configurable defaults are deliberately conservative for scheduled data evidence rather than assumed service-request traffic.

Remaining budget states are healthy at 50% or more, at risk from 10% to 50%, critical below 10%, and exhausted at or below zero. Partial evidence overrides a healthy presentation. Forecasting is withheld until a service has sufficient stable history, non-partial coverage, and positive burn.
