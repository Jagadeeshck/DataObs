# Pathway Explorer

Pathway Explorer executes a tenant- and environment-scoped product query and presents deterministic ranked complete and partial routes. Traversal is bounded by hops, alternatives, nodes, edges, timeout, confidence and active-evidence filters. Route ranking is explainable and never uses an opaque model. Structural evidence is labelled separately from observed pipeline lineage.

The browser cancels superseded requests, stores search inputs in the URL, renders the selected route, and provides a semantic table as the graph alternative. Missing metric sources remain explicit rather than becoming zero.

The current topology-loading query is an acknowledged completion blocker at enterprise scale. Approval requires Elasticsearch adjacency or precomputed route projections so each expansion is bounded and tenant-scoped rather than downloading an arbitrary graph.

> Pathway Explorer explains how data travels, where delay or failure accumulates, and what is affected. Asset 360 explains the complete observed state of one asset. Kibana remains the deep investigation surface.
