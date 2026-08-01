# Run comparison

`POST /api/v1/runs/compare` compares tenant- and environment-bound runs. Different jobs require explicit opt-in and produce a warning. Numeric deltas preserve zero as a value and use `null` when either observation is missing; percentage deltas avoid a zero denominator.

Comparison covers run state, duration and delays plus bounded task/stage, critical-path, asset, resource, quality, code, and deployment evidence as those fields are observed. Confidence falls with missing evidence rather than inventing equivalence.
