# Incident correlation v1

Correlation is distinct from deduplication: deduplication reconciles replay of the same finding, while correlation associates distinct, durably retained incidents. The immutable `dataobs-incident-correlation` v1 policy compares bounded safe projection fields, records unavailable evidence separately, and scores only available evidence. Candidate retrieval is required to be tenant/environment scoped, within the event-time window, lifecycle filtered, deterministically ordered, capped at 100, and backed by allowlisted Elasticsearch predicates.

A deterministic correlation decision identifies the tenant, environment, incident revision, and policy version. A separate correlation-group projection retains a deterministic sample and exact count; it never changes stable incident identity or deletes evidence. Representatives sort by severity, confirmed business impact, critical service/product impact, earliest observation, then incident ID. “Related” means shared evidence and temporal association, never causation. Policy name, version, canonical SHA-256 hash, evaluation time, score, confidence, reason codes, missing inputs, and evidence states make decisions explainable and rolling-version safe.

Production repositories must use OCC, refetch and recompute after conflicts, append decisions to `logs-dataobs.correlation_event-*`, and store compatible projections in `dataobs-incident-correlations-v1`. Deferred work is reconciled after incident persistence.

## Runtime v1 production contract

The durable runtime, storage/OCC/idempotency boundaries, deferred recovery, security bounds and current certification limitations are specified in [Incident correlation runtime](incident-correlation-runtime.md) and [Event Storm runtime](event-storm-runtime.md), with operator procedures in the corresponding operations runbooks. Correlation associates evidence without deleting incidents; flood control changes notification intent without discarding ingestion.
