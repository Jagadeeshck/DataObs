# Stream anomaly, retention and failure intelligence

Team 1 intelligence consumes bounded historical stream/pathway evidence and reuses reliability identity, trusted scope, lease/fencing, OCC and append-before-projection ordering. It does not replace reliability evaluation.

The bounded algorithm registry contains robust z-score/MAD, EWMA deviation, relative/rate change, trend forecast, seasonal bucket, partition skew, retention exhaustion and failure pattern. MAD baselines preserve zero, discard non-finite input, record quantiles/sample coverage and apply an explicit constant-series change policy. Cold starts are `insufficient_data`, never normal. Seasonal claims require enough bucket samples and cycles; otherwise the algorithm records a non-seasonal fallback. UTC is default; named-zone daylight-saving buckets follow the stored local wall-clock bucket and may contain repeated/missing hours.

Transitions require consecutive abnormal evaluations, except severe threshold crossings; recovery uses a separate count and hysteresis. Signals are transition/repeat-window events rather than per-evaluation noise.

Drain uses `consumer_rate - producer_rate`; non-positive effective drain yields `not_draining` with no finite drain duration. Time retention requires record-age evidence and configured retention. Byte retention distinguishes consumer exposure from topic storage and broker disk risk. Lower/expected/upper estimates are deterministic ranges only when sufficient rate evidence exists—not confidence intervals. `data_loss_suspected` requires authoritative offset-outside-retention evidence.

Partition skew uses median/MAD, preserves partition zero, caps sorted affected IDs, reports missing coverage and never labels a one-partition topic skewed. Failure intelligence persists metadata-only `poison_message_candidate` classifications. Change overlays are correlated evidence, never root-cause claims.

Persistence order is: fenced lease check, definition/state load, bounded evidence query, validation, calculation, append evaluation, OCC projection, idempotent transition signal, checkpoint, health. Projection failure blocks checkpoint advancement; signal failures remain pending reconciliation.

