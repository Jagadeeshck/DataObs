# Incident similarity intelligence

Similarity is an evidence comparison, not causality, correlation, duplication, or recurrence. `incident-features/1.0.0` normalizes bounded categorical evidence and `incident-similarity/1.0.0` scores available features only. Empty evidence is unavailable, not a match or mismatch. The response contains server-authored matches, differences, unavailable features, coverage, confidence, classification, revisions, and computation time.

The canonical weights are primary asset 0.16, affected assets 0.10, finding types 0.11, signal types 0.05, resource IDs 0.06, rule IDs 0.13, failure categories 0.13, correlation key 0.05, correlation feature keys 0.04, Data Products 0.07, business services 0.03, confirmed root-cause category 0.04, and recovery characteristics 0.03. Available weights are normalized to 1.0 for similarity. Coverage retains their absolute available share. Confidence combines coverage, reliability, and independent matching-family breadth.

The structural fingerprint excludes incident identity, revisions, timestamps, people, free text, logs, and evidence payloads. Equality means `same_structural_signature` only.

Elasticsearch candidate generation has immutable tenant and environment predicates, an allowlisted 30/90/180/365-day horizon, at least one structural prefilter, a 200-hit ceiling, and deterministic sorting. The application scores only this bounded pool and returns at most 20 results.
