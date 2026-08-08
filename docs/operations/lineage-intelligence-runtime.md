# Lineage intelligence runtime

The v1 API performs deterministic replay-safe evaluation and writes append-only evidence. A continuously scheduled lease/checkpoint worker is not enabled in this change; runtime health must therefore be reported as `not_configured`, not healthy. Operators may recompute an analysis using the persisted request identity. Checkpoints must never advance after partial writes when a worker is introduced.
