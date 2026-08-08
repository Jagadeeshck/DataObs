# Search ranking and deduplication

Ordering is exact identifier, exact label, label prefix, token prefix, then provider ordering. Provider ID and stable result key break ties. Deduplication uses entity type plus opaque identifier before the global 25-result limit. This is deterministic string ranking, not AI relevance. Missing and stale evidence do not receive a ranking advantage.
