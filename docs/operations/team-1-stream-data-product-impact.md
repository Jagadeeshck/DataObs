# Operating stream-to-Data-Product impact

Product enrichment is optional and failure-isolated. Timeouts or connection failures map to
`product_context_status=unavailable`, never an empty/healthy result. Permission failures map to `permission_denied` and
must not disclose product, owner, or support metadata. Investigate missing inputs individually (`no_binding_found`,
`product_service_unavailable`, `lineage_unavailable`, `pathway_partial`, `slo_not_configured`,
`slo_evidence_missing`, `permission_denied`, or `history_unavailable`).

The resolver uses trusted tenant and environment values supplied by server request context. Operators should monitor
read-port latency, timeout counts, truncation, missing evidence, and stale SLO context. The core Stream 360 and Pathway
360 experiences must remain available during Team 2 outages.
