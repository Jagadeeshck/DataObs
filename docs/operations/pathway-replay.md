# Pathway replay

Normal processing re-reads the configured overlap interval before the committed
event watermark. Append-only observation IDs are derived from edge and source
document identity, making the overlap idempotent while allowing late documents
to update current projections.

Run `dataobs-pathway-worker replay --replay-minutes N` for a bounded manual
replay. The supported bound is one minute through 31 days. Replays remain
tenant/environment scoped, acquire the same fenced lease, and never inspect or
persist Kafka message contents. Increase the overlap only when source lateness
requires it; a larger window increases read load but not observation duplicates.
