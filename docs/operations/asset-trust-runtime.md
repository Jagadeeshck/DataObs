# Asset Trust runtime

Events enqueue the scoped affected asset and a reason. Duplicate requests merge.
Workers claim at most 500 assets, with 100 the default, using a lease owner, expiry,
attempt count, and monotonically increasing fencing token. A worker must present
the current owner and token to complete work; takeover makes an expired worker's
write ineligible. Score IDs make replay idempotent and history is append-only.

Operational health reports pending assets and oldest pending age. Production
adapters should additionally expose checkpoint, last success/failure, evaluation
rate, lease conflicts, and Elasticsearch connectivity using bounded metric labels.
