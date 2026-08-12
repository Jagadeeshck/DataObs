# dbt test and freshness intelligence

Test definitions and run-result observations are separate. Statuses are `pass`, `warn`, `fail`, `error`, `skipped`, and `unknown`; skipped or absent evidence is never success. Flakiness requires mixed passes/failures and multiple transitions with at least five observations. A history containing only failures is `consistently_failing`.

Source freshness normalizes pass/warn/error/runtime-error evidence and preserves zero ages. It is evidence for the canonical freshness monitor, not another freshness engine. Missing monitor configuration is surfaced and never creates a monitor automatically. Coverage signals are governance gaps rather than assertions that an untested column is bad.
