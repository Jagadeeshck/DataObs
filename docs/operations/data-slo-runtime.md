# Data SLO runtime

The runtime should reuse monitor-runtime claim, lease, renewal, fencing, checkpoint, restart, and takeover conventions. Each bounded cycle resolves an immutable definition revision, aggregates canonical evidence, evaluates intervals, appends an evaluation, updates its OCC current projection, and emits a canonical finding only on meaningful transitions. Health includes last success, due count, backlog, oldest due, lease conflicts, and failures. Telemetry must not label metrics with SLO or asset IDs.
