# Incident correlation runtime

The v1 pure engine scores bounded safe evidence; the coordinator owns persistence and never makes causal claims. A group begins with a deterministic identity derived from tenant, environment, first incident and policy identity. Existing matching groups retain their ID. Concurrent creates converge through create-only writes and bounded OCC refetch/recompute retries. Related existing groups produce no automatic merge; merge review remains future work.

Elasticsearch candidate retrieval is tenant/environment scoped, time bounded, restricted to active compatible v1 projections, uses allowlisted topology terms, a two-second timeout, at most 50 hits, deterministic time/ID sorting and an explicit source allowlist. Groups are preferred; the first incident always establishes a group so no unbounded incident scan is required.

The strict group adapter places searchable scope, identity, representative, topology, severity, confidence, counts and timestamps in mapped fields. Policy identity, exact count, evidence coverage, reason codes and truncation state are bounded metadata. The member sample is never described as complete; append-only decisions reconstruct membership.

Decision IDs bind scope, incident revision, selected group and policy name/version/hash. Create-only event writes make replay idempotent. Group update uses Elasticsearch sequence number/primary term OCC and retries only missing membership.

The capability is `functional_unvalidated` until exact-head real-stack evidence is retained and independently verified.
