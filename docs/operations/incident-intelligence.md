# Operating incident intelligence

Candidate searches are bounded to one tenant, one environment, an allowlisted horizon, 200 Elasticsearch candidates, and 20 returned results. A search with no safe structural prefilter returns no candidates. Do not add all-time scans or pairwise materialization.

Monitor low-cardinality query, latency, candidate, confirmed, rejected, projection, and projection-failure counters. Labels are limited to result, classification, and operation. Never label telemetry with tenant, incident, family, asset, or product IDs.

Rebuild tooling must require tenant, environment, start/end dates, and batch size before it is production-enabled. Elasticsearch 9.4.2 and browser certification remain required before promotion beyond `functional_unvalidated`.
