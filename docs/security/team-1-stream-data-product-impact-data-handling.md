# Stream Product Exposure data handling

The feature handles metadata only. All reads are tenant- and environment-scoped using trusted request state; caller
query/body scope is not accepted. Authorization is evaluated before product metadata is returned. Evidence references
are bounded and must not contain payloads, secrets, or arbitrary Elasticsearch queries.

Candidate resolution uses canonical/provider resource IDs, entity IDs, application IDs, or pathway IDs. It never scans
all products, fuzzy-matches names, infers owners/business services, or crosses tenant/environment boundaries. Team 1
does not write Data Product, membership, lineage, SLO, or Team 2 impact indices.
