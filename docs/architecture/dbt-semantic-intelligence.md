# dbt semantic intelligence

Manifest semantic models, metrics, saved queries, exposures and groups are normalized as metadata. Dependency edges are typed as semantic or consumer dependencies, distinct from physical runtime movement. Unresolved references do not create edges and traversal is bounded.

Entity, dimension and measure metadata is identifier-only and bounded. Expressions are not retained. Saved-query filters are represented by `has_filter` and a deterministic fingerprint. This capability does not execute metrics or compete with the dbt Semantic Layer.
