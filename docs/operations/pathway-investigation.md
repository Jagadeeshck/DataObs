# Operating pathway investigation

Run the existing pathway worker with history projection enabled after migration 0028. The projector compares canonical hashes, uses the worker fencing token, suppresses duplicates, and emits a daily safety snapshot. Monitor snapshot age, latest source time, fencing conflicts, query count and bounded graph sizes using low-cardinality labels.

Read endpoints are `/snapshot`, `/history`, `/blast-radius`, `/compare`, `/investigation-timeline`, and `/investigation-evidence`. Rollback stops writers, preserves append-only snapshots, exports evidence, then removes write aliases; historical evidence is not rewritten. There is no synthetic backfill because pre-enable complete topology cannot be proven. Current limitations are partial change/deployment/rebalance coverage and optional Team 2/3 provider availability.
